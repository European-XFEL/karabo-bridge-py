from karabo_bridge.cli import glimpse

def test_main(sim_server, capsys):
    glimpse.main([sim_server])
    out, err = capsys.readouterr()
    assert 'SPB_DET_AGIPD1M-1/DET/detector' in out
