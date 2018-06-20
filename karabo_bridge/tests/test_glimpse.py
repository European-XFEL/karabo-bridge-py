import os

import h5py
from testpath.tempdir import TemporaryWorkingDirectory

from karabo_bridge.cli import glimpse


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
            trainId = f['SPB_DET_AGIPD1M-1/DET/detector/trainId'].value
            assert trainId == 10000000000
