import numpy as np
import pytest

from karabo_bridge import serialize, deserialize

from .utils import compare_nested_dict


def test_serialize(data, protocol_version):
    msg = serialize(data, protocol_version=protocol_version)
    assert isinstance(msg, list)

    d, m = deserialize(msg)
    compare_nested_dict(data, d)
    assert m['source1'] == {'timestamp.tid': 9876543210, 'timestamp': 12345678}
    assert m['XMPL/DET/MOD0'] == {}


def test_serialize_with_metadata(data, metadata, protocol_version):
    msg = serialize(data, metadata, protocol_version=protocol_version)

    d, m = deserialize(msg)
    compare_nested_dict(metadata, m)


def test_serialize_with_dummy_timestamps(data, protocol_version):
    msg = serialize(data, protocol_version=protocol_version,
                    dummy_timestamps=True)

    d, m = deserialize(msg)
    assert set(m['XMPL/DET/MOD0']) == {'timestamp', 'timestamp.sec', 'timestamp.frac'}
    assert set(m['source1']) == {'timestamp', 'timestamp.tid'}
    assert m['source1']['timestamp.tid'] == 9876543210
    assert m['source1']['timestamp'] == 12345678


def test_serialize_with_metadata_and_dummy_timestamp(data, metadata, protocol_version):
    msg = serialize(data, metadata, protocol_version=protocol_version,
                    dummy_timestamps=True)

    d, m = deserialize(msg)
    compare_nested_dict(metadata, m)


def test_wrong_version(data):
    with pytest.raises(ValueError):
        serialize(data, protocol_version='3.0')
