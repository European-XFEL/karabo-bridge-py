from queue import Full
import pytest

from karabo_bridge import Client

from .utils import compare_nested_dict


def test_fill_queue(server, data):
    for _ in range(10):
        server.feed(data)

    assert server.buffer.full()
    with pytest.raises(Full):
        server.feed(data, block=False)

    for _ in range(10):
        assert server.buffer.get() == (data, None)


def test_req_rep(server, data):
    for _ in range(3):
        server.feed(data)

    with Client(server.endpoint) as client:
        for _ in range(3):
            d, m = client.next()
            compare_nested_dict(data, d)
