from karabo_bridge import Client

def test_get_frame(sim_server):
    c = Client(sim_server)
    data, metadata = c.next()
    assert 'SPB_DET_AGIPD1M-1/DET/detector' in data
    assert 'SPB_DET_AGIPD1M-1/DET/detector' in metadata
