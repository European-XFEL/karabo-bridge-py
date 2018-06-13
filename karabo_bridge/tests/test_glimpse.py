from karabo_bridge.cli import glimpse
import h5py
import os
from testpath.tempdir import TemporaryWorkingDirectory


def test_main(sim_server, capsys):
    glimpse.main([sim_server])
    out, err = capsys.readouterr()
    assert 'SPB_DET_AGIPD1M-1/DET/detector' in out

def test_save(sim_server):
    with TemporaryWorkingDirectory() as td:
        glimpse.main(['--save', sim_server])
        files = os.listdir(td)
        print(files)
        assert len(files) == 1
        path = os.path.join(td, files[0])
        with h5py.File(path, 'r') as f:
            assert f['SPB_DET_AGIPD1M-1/DET/detector/image.trainId'].shape == (64,)

