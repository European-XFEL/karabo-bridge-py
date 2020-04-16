from functools import partial
from time import time

import msgpack
import msgpack_numpy
import numpy as np
import zmq


__all__ = ['serialize', 'deserialize']


class Frame:
    def __init__(self, data):
        """Dummy zmq.Frame object

        deserialize() expects the message in ZMQ Frame objects.
        """
        self.bytes = data
        self.buffer = data


def timestamp():
    """Generate dummy timestamp information based on machine time
    """
    epoch = time()
    sec, frac = str(epoch).split('.')
    frac = frac.ljust(18, '0')
    return {
        'timestamp': epoch,
        'timestamp.sec': sec,
        'timestamp.frac': frac,
    }


def _serialize_old(data, metadata, dummy_timestamps):
    """Adapter for backward compatibility with protocol 1.0
    """
    ts = timestamp()
    new_data = {}
    for src, val in data.items():
        # in version 1.0 metadata is contained in data[src]['metadata']
        # We need to make a copy to not alter the original data dict
        new_data[src] = val.copy()
        meta = metadata[src].copy()
        if dummy_timestamps and 'timestamp' not in meta:
            meta.update(ts)
        new_data[src]['metadata'] = meta

    return [msgpack.packb(new_data, use_bin_type=True,
                          default=msgpack_numpy.encode)]


def serialize(data, metadata=None, protocol_version='2.2',
              dummy_timestamps=False):
    """Serializer for the Karabo bridge protocol

    Convert data/metadata to a list of bytestrings and/or memoryviews

    Parameters
    ----------
    data : dict
        Contains train data. The dictionary has to follow the karabo_bridge
        protocol structure:

        - keys are source names
        - values are dict, where the keys are the parameter names and
            values must be python built-in types or numpy.ndarray.

    metadata : dict, optional
        Contains train metadata. The dictionary has to follow the
        karabo_bridge protocol structure:

        - keys are (str) source names
        - values (dict) should contain the following items:

            - 'timestamp' Unix time with subsecond resolution
            - 'timestamp.sec' Unix time with second resolution
            - 'timestamp.frac' fractional part with attosecond resolution
            - 'timestamp.tid' is European XFEL train unique ID

        ::

            {
                'source': 'sourceName'  # str
                'timestamp': 1234.567890  # float
                'timestamp.sec': '1234'  # str
                'timestamp.frac': '567890000000000000'  # str
                'timestamp.tid': 1234567890  # int
            }

        If the metadata dict is not provided it will be extracted from
        'data' or an empty dict if 'metadata' key is missing from a data
        source.

    protocol_version: ('1.0' | '2.2')
        Which version of the bridge protocol to use. Defaults to the latest
        version implemented.

    dummy_timestamps: bool
        Some tools (such as OnDA) expect the timestamp information to be in the
        messages. We can't give accurate timestamps where these are not in the
        file, so this option generates fake timestamps from the time the data
        is fed in, if the real timestamp information is missing.

    returns
    -------
    msg: list of bytes/memoryviews ojects
        binary conversion of data/metadata readable by the karabo_bridge
    """
    if protocol_version not in {'1.0', '2.2'}:
        raise ValueError(f'Unknown protocol version {protocol_version}')

    if metadata is None:
        metadata = {src: v.get('metadata', {}) for src, v in data.items()}

    if protocol_version == '1.0':
        return _serialize_old(data, metadata, dummy_timestamps)

    pack = msgpack.Packer(use_bin_type=True).pack
    msg = []
    ts = timestamp()
    for src, props in sorted(data.items()):
        src_meta = metadata[src].copy()
        if dummy_timestamps and 'timestamp' not in src_meta:
            src_meta.update(ts)

        main_data = {}
        arrays = []
        for key, value in props.items():
            if isinstance(value, np.ndarray):
                arrays.append((key, value))
            elif isinstance(value, np.number):
                # Convert numpy type to native Python type
                main_data[key] = value.item()
            else:
                main_data[key] = value

        msg.extend([
            pack({
                'source': src, 'content': 'msgpack',
                'metadata': src_meta
            }),
            pack(main_data)
        ])

        for key, array in arrays:
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            msg.extend([
                pack({
                    'source': src, 'content': 'array', 'path': key,
                    'dtype': str(array.dtype), 'shape': array.shape
                }),
                array.data,
            ])

    return msg


def deserialize(msg):
    """Deserializer for the karabo bridge protocol

    Parameters
    ----------
    msg: list of zmq.Frame or list of byte objects
        Serialized data following the karabo_bridge protocol

    Returns
    -------
    data : dict
        The data for a train, keyed by source name.
    meta : dict
        The metadata for a train, keyed by source name.
    """
    unpack = partial(msgpack.loads, raw=False, max_bin_len=0x7fffffff)

    if not isinstance(msg[0], zmq.Frame):
        msg = [Frame(m) for m in msg]

    if len(msg) < 2:  # protocol version 1.0
        data = unpack(msg[-1].bytes, object_hook=msgpack_numpy.decode)
        meta = {}
        for key, value in data.items():
            meta[key] = value.get('metadata', {})
        return data, meta

    data, meta = {}, {}
    for header, payload in zip(*[iter(msg)]*2):
        md = unpack(header.bytes)
        source = md['source']
        content = md['content']

        if content == 'msgpack':
            data[source] = unpack(payload.bytes)
            meta[source] = md.get('metadata', {})
        elif content == 'array':
            dtype, shape = md['dtype'], md['shape']
            array = np.frombuffer(payload.buffer, dtype=dtype).reshape(shape)
            data[source].update({md['path']: array})
        else:
            raise RuntimeError('Unknown message: %s' % md['content'])
    return data, meta
