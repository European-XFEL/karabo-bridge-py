from karabo_bridge.qt import QBridgeClient

def test_receive_n(sim_server, qtbot, qapp):
    qbc = QBridgeClient(sim_server.endpoint)
    results = []
    def data_received(data, metadata):
        results.append((data, metadata))
    qbc.new_data.connect(data_received)

    with qtbot.waitSignal(qbc.stopped, timeout=5000):
        qbc.start(stop_after=2)
        assert qbc.is_active

    qapp.processEvents()

    assert not qbc.is_active

    assert len(results) == 2
    for data, metadata in results:
        assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in data
        assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in metadata

    # Check that we can start receiving again after stopping
    with qtbot.waitSignal(qbc.stopped, timeout=5000):
        qbc.start(stop_after=2)

    qapp.processEvents()

    assert len(results) == 4


def test_receive_indefinite(sim_server, qtbot):
    qbc = QBridgeClient(sim_server.endpoint)
    n_recvd = 0
    def data_received(data, metadata):
        nonlocal n_recvd
        n_recvd += 1
        if n_recvd >= 5:
            qbc.stop()

    qbc.new_data.connect(data_received)

    with qtbot.waitSignal(qbc.stopped, timeout=5000):
        qbc.start()

    assert not qbc.is_active

    assert n_recvd == 5
