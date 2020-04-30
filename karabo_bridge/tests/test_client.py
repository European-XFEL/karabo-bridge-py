from itertools import islice

import pytest

from karabo_bridge import Client


def test_get_frame(sim_server, protocol_version):
    c = Client(sim_server.endpoint)
    data, metadata = c.next()
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in data
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in metadata
    if protocol_version == '1.0':
        assert all('metadata' in src for src in data.values())


def test_pull_socket(sim_push_server):
    c = Client(sim_push_server.endpoint, sock='PULL')
    data, metadata = c.next()
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in data
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in metadata


def test_pair_socket(sim_server):
    with pytest.raises(NotImplementedError):
        c = Client(sim_server, sock='PAIR')


def test_context_manager(sim_server):
    with Client(sim_server.endpoint) as c:
        data, metadata = c.next()
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in data
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in metadata
    assert c._socket.closed


def test_iterator(sim_server):
    c = Client(sim_server.endpoint)
    for i, (data, metadata) in enumerate(islice(c, 3)):
        trainId = metadata['SPB_DET_AGIPD1M-1/DET/0CH0:xtdf']['timestamp.tid']
        assert trainId == 10000000000 + i


def test_timeout():
    no_server = 'ipc://nodata'
    with Client(no_server, timeout=0.2) as c:
        for _ in range(3):
            with pytest.raises(TimeoutError) as info:
                tid, data = c.next()

    assert 'No data received from ipc://nodata in the last 200 ms' in str(info.value)
