from karabo_bridge.cli import monitor

def test_main(sim_server, capsys):
    monitor.main([sim_server, '--ntrains', '1'])
    out, err = capsys.readouterr()
    assert 'SPB_DET_AGIPD1M-1/DET/detector' in out
