"""Inspect a single message from Karabo bridge.
"""

import argparse
from collections import Sequence
from datetime import datetime
import h5py
import numpy as np
from socket import gethostname
from time import localtime, strftime, time

from .. import Client


def gen_filename(endpoint):
    """Generate a filename from endpoint with timestamp.

    return: str
        hostname_port_YearMonthDay_HourMinSecFrac.h5
    """
    now = datetime.now().strftime('%Y%m%d_%H%M%S%f')[:-4]
    base = endpoint.split('://', 1)[1]
    if base.startswith('localhost:'):
        base = gethostname().split('.')[0] + base[9:]
    base = base.replace(':', '_').replace('/', '_')
    return '{}_{}.h5'.format(base, now)


def dict_to_hdf5(dic, endpoint):
    """Dump a dict to an HDF5 file.
    """
    filename = gen_filename(endpoint)
    with h5py.File(filename, 'w') as handler:
        walk_dict_to_hdf5(dic, handler)
    print('dumped to', filename)


def hdf5_to_dict(filepath, group='/'):
    """load the content of an hdf5 file to a dict.

    # TODO: how to split domain_type_dev : parameter : value ?
    """
    if not h5py.is_hdf5(filepath):
        raise RuntimeError(filepath, 'is not a valid HDF5 file.')

    with h5py.File(filepath, 'r') as handler:
        dic = walk_hdf5_to_dict(handler[group])
    return dic


vlen_bytes = h5py.special_dtype(vlen=bytes)
vlen_str = h5py.special_dtype(vlen=str)


def walk_dict_to_hdf5(dic, h5):
    for key, value in sorted(dic.items()):
        if isinstance(value, dict):
            group = h5.create_group(key)
            walk_dict_to_hdf5(value, group)
        elif isinstance(value, (np.ndarray)):
            h5.create_dataset(key, data=value, dtype=value.dtype)
        elif isinstance(value, (int, float)):
            h5.create_dataset(key, data=value, dtype=type(value))
        elif isinstance(value, str):
            # VLEN strings do not support embedded NULLs
            value = value.replace('\x00', '')
            ds = h5.create_dataset(key, shape=(len(value), ),
                                   dtype=vlen_str, maxshape=(None, ))
            ds[:len(value)] = value
        elif isinstance(value, bytes):
            # VLEN strings do not support embedded NULLs
            value = value.replace(b'\x00', b'')
            ds = h5.create_dataset(key, shape=(len(value), ),
                                   dtype=vlen_bytes, maxshape=(None, ))
            ds[:len(value)] = value
        else:
            print('not supported', type(value))


def walk_hdf5_to_dict(h5):
    dic = {}
    for key, value in h5.items():
        if isinstance(value, h5py.Group):
            dic[key] = walk_hdf5_to_dict(value)
        elif isinstance(value, h5py.Dataset):
            dic[key] = value[()]
        else:
            print('what are you?', type(value))
    return dic


def print_one_train(client, verbosity=0):
    """Retrieve data for one train and print it.

    Returns the (data, metadata) dicts from the client.

    This is used by the -glimpse and -monitor command line tools.
    """
    ts_before = time()
    data, meta = client.next()
    ts_after = time()

    if not data:
        print("Empty data")
        return

    train_id = list(meta.values())[0].get('timestamp.tid', 0)
    print("Train ID:", train_id, "--------------------------")
    delta = ts_after - ts_before
    print('Data from {} sources, REQ-REP took {:.2f} ms'
          .format(len(data), delta))
    print()

    for i, (source, src_data) in enumerate(sorted(data.items()), start=1):
        src_metadata = meta.get(source, {})
        tid = src_metadata.get('timestamp.tid', 0)
        print("Source {}: {!r} @ {}".format(i, source, tid))
        try:
            ts = src_metadata['timestamp']
        except KeyError:
            print("No timestamp")
        else:
            dt = strftime('%Y-%m-%d %H:%M:%S', localtime(ts))

            delay = (ts_after - ts) * 1000
            print('timestamp: {} ({}) | delay: {:.2f} ms'
                  .format(dt, ts, delay))

        if verbosity < 1:
            print("- data:", sorted(src_data))
            print("- metadata:", sorted(src_metadata))
        else:
            print('data:')
            pretty_print(src_data, verbosity=verbosity - 1)
            if src_metadata:
                print('metadata:')
                pretty_print(src_metadata)
        print()

    return data, meta


def pretty_print(d, ind='', verbosity=0):
    """Pretty print a data dictionary from the bridge client
    """
    assert isinstance(d, dict)
    for k, v in sorted(d.items()):
        str_base = '{} - [{}] {}'.format(ind, type(v).__name__, k)

        if isinstance(v, dict):
            print(str_base.replace('-', '+', 1))
            pretty_print(v, ind=ind+'  ', verbosity=verbosity)
            continue
        elif isinstance(v, np.ndarray):
            node = '{}, {}, {}'.format(str_base, v.dtype, v.shape)
            if verbosity >= 2:
                node += '\n{}'.format(v)
        elif isinstance(v, Sequence):
            if v and isinstance(v, (list, tuple)):
                itemtype = ' of ' + type(v[0]).__name__
                pos = str_base.find(']')
                str_base = str_base[:pos] + itemtype + str_base[pos:]
            node = '{}, {}'.format(str_base, v)
            if verbosity < 1 and len(node) > 80:
                node = node[:77] + '...'
        else:
            node = '{}, {}'.format(str_base, v)
        print(node)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-glimpse",
        description="Get one Karabo bridge message and prints its data"
                    "structure. optionally: save its data to an HDF5 file.")
    ap.add_argument('endpoint',
                    help="ZMQ address to connect to, e.g. 'tcp://localhost:4545'")
    ap.add_argument('-z', '--server-socket', default='REP', choices=['REP', 'PUB', 'PUSH'],
                    help='Socket type used by the karabo bridge server (default REP)')
    ap.add_argument('-s', '--save', action='store_true',
                    help='Save the received train data to a HDF5 file')
    ap.add_argument('-v', '--verbose', action='count', default=0,
                    help='Select verbosity (-vv for most verbose)')
    args = ap.parse_args(argv)

    # use the appropriate client socket type to match the server
    socket_map = {'REP': 'REQ', 'PUB': 'SUB', 'PUSH': 'PULL'}
    client = Client(args.endpoint, sock=socket_map[args.server_socket])
    data, _ = print_one_train(client, verbosity=args.verbose + 1)

    if args.save:
        dict_to_hdf5(data, args.endpoint)
