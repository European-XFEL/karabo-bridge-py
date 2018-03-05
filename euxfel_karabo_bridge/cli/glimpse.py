from datetime import datetime
import h5py
import numpy as np
import os.path as osp
from socket import gethostname
import sys

from .utils import entrypoint
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


@entrypoint
def main():
    """Karabo bridge glimpse.

    Get a single train data from a karabo bridge server and dump it to a file.
    
      krbb_glimpse [host] [port]
      
    e.g.    
      krbb_glimpse 10.254.0.64 4500
    """
    assert len(sys.argv) > 2
    _, host, port, *options = sys.argv
    assert port.isdigit()

    endpoint = 'tcp://{}:{}'.format(host, port)
    print('get train data from', endpoint)

    client = Client(endpoint)
    data = client.next()

    dict_to_hdf5(data, endpoint)


if __name__ == '__main__':
    main()
