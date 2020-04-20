from karabo_bridge.cli import monitor


def test_main(sim_server, capsys):
    monitor.main([sim_server.endpoint, '--ntrains', '1'])
    out, err = capsys.readouterr()
    assert 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf' in out
