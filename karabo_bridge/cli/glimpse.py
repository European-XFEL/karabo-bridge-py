import argparse
from collections import Sequence
from datetime import datetime
import h5py
import numpy as np
from socket import gethostname

from .. import Client


def gen_filename(endpoint):
    """Generate a filename from endpoint with timestamp.

    return: str
        hostname_port_YearMonthDay_HourMinSecFrac.h5
    """
    now = datetime.now().strftime('%Y%m%d_%H%M%S%f')[:-4]
    _, host, port = endpoint.replace('/', '').split(':')
    if host == 'localhost':
        host = gethostname().split('.')[0]
    return '{}_{}_{}.h5'.format(host, port, now)


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


def walk_dict_to_hdf5(dic, h5):
    for key, value in dic.items():
        if isinstance(value, dict):
            group = h5.create_group(key)
            walk_dict_to_hdf5(value, group)
        elif isinstance(value, (np.ndarray)):
            h5.create_dataset(key, data=value, dtype=value.dtype)
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


def pretty_print(d, ind=''):
    try:
        assert isinstance(d, dict)
    except AssertionError:
        print(type(d))
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            print('{}+ [{}] {}'.format(ind, type(v).__name__, k))
            pretty_print(v, ind=ind+'  ')
            continue
        elif isinstance(v, np.ndarray):
            node = '{}- [{}] {}, {}, {}'.format(
                ind, type(v).__name__, k, v.dtype, v.shape)
        elif isinstance(v, (bytes, bytearray, memoryview, Sequence)):
            strv = str(v)
            node = '{}- [{}] {}, '.format(ind, type(v).__name__, k)
            node += strv[:77-len(node)]+'...' if len(strv) > 77-len(node) else strv
        else:
            node = '{}- [{}] {}, {}'.format(ind, type(v).__name__, k, v)
        print(node)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-glimpse",
        description="Get one Karabo bridge message and prints its data"
                    "structure. optionally: save its data to an HDF5 file.")
    ap.add_argument('endpoint',
                    help="ZMQ address to connect to, e.g. 'tcp://localhost:4545'")
    ap.add_argument('-s', '--save', action='store_true',
                    help='Save the received train data to a HDF5 file.')
    args = ap.parse_args(argv)

    client = Client(args.endpoint)
    data = client.next()

    if isinstance(data, tuple):
        data, meta = data

    for k, v in data.items():
        print('\n*** data source: "%s" \ndata:' % k)
        pretty_print(v)
        if meta[k]:
            print('metadata:')
            pretty_print(meta[k])

    if args.save:
        dict_to_hdf5(data, args.endpoint)
