import numpy as np
import pytest

from karabo_bridge import serialize, deserialize


@pytest.fixture(scope='session')
def data():
    yield {
        'source1': {
            'parameter.1.value': 123,
            'parameter.2.value': 1.23,
            'list.of.int': [1, 2, 3],
            'string.param': 'True',
            'boolean': False,
            'metadata': {'timestamp.tid': 9876543210, 'timestamp': 12345678},
        },
        'XMPL/DET/MOD0': {
            'image.data': np.random.randint(255, size=(2, 3, 4), dtype=np.uint8),
            'something.else': ['a', 'bc', 'd'],
        },
    }


@pytest.fixture(scope='session')
def metadata():
    yield {
        'source1': {
            'source': 'source1',
            'timestamp': 1585926035.7098422,
            'timestamp.sec': '1585926035',
            'timestamp.frac': '709842200000000000',
            'timestamp.tid': 1000000
        },
        'XMPL/DET/MOD0': {
            'source': 'XMPL/DET/MOD0',
            'timestamp': 1585926036.9098422,
            'timestamp.sec': '1585926036',
            'timestamp.frac': '909842200000000000',
            'timestamp.tid': 1000010
        }
    }


def compare_nested_dict(d1, d2, path=''):
    for key in d1.keys():
        if key not in d2:
            print(d1.keys())
            print(d2.keys())
            raise KeyError('key is missing in d2: {}{}'.format(path, key))

        if isinstance(d1[key], dict):
            path += key + '.'
            compare_nested_dict(d1[key], d2[key], path)
        else:
            v1 = d1[key]
            v2 = d2[key]

            try:
                if isinstance(v1, np.ndarray):
                    assert (v1 == v2).all()
                elif isinstance(v1, tuple) or isinstance(v2, tuple):
                    # msgpack doesn't know about complex types, everything is
                    # an array. So tuples are packed as array and then
                    # unpacked as list by default.
                    assert list(v1) == list(v2)
                else:
                    assert v1 == v2
            except AssertionError:
                raise ValueError('diff: {}{}'.format(path, key), v1, v2)


@pytest.mark.parametrize('protocol_version', ['1.0', '2.2'])
def test_serialize(data, protocol_version):
    msg = serialize(data, protocol_version=protocol_version)
    assert isinstance(msg, list)

    d, m = deserialize(msg)
    compare_nested_dict(data, d)

    assert m['source1'] == {'timestamp.tid': 9876543210, 'timestamp': 12345678}
    assert m['XMPL/DET/MOD0'] == {}


@pytest.mark.parametrize('protocol_version', ['1.0', '2.2'])
def test_serialize_with_metadata(data, metadata, protocol_version):
    msg = serialize(data, metadata, protocol_version=protocol_version)

    d, m = deserialize(msg)
    compare_nested_dict(metadata, m)


@pytest.mark.parametrize('protocol_version', ['1.0', '2.2'])
def test_serialize_with_dummy_timestamps(data, protocol_version):
    msg = serialize(data, protocol_version=protocol_version,
                    dummy_timestamps=True)

    d, m = deserialize(msg)
    assert set(m['XMPL/DET/MOD0']) == {'timestamp', 'timestamp.sec', 'timestamp.frac'}
    assert set(m['source1']) == {'timestamp', 'timestamp.tid'}
    assert m['source1']['timestamp.tid'] == 9876543210
    assert m['source1']['timestamp'] == 12345678


@pytest.mark.parametrize('protocol_version', ['1.0', '2.2'])
def test_serialize_with_metadata_and_dummy_timestamp(data, metadata, protocol_version):
    msg = serialize(data, metadata, protocol_version=protocol_version,
                    dummy_timestamps=True)

    d, m = deserialize(msg)
    compare_nested_dict(metadata, m)


def test_wrong_version(data):
    with pytest.raises(ValueError):
        serialize(data, protocol_version='3.0')
