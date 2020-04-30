from karabo_bridge import Client

from .utils import compare_nested_dict


def test_req_rep(server, data):
    for _ in range(3):
        server.feed(data)

    with Client(server.endpoint) as client:
        for _ in range(3):
            d, m = client.next()
            compare_nested_dict(data, d)
