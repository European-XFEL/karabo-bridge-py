import numpy as np

from karabo_bridge.simulation import Detector


source_lpd = 'FXE_DET_LPD1M-1/CAL/APPEND_CORRECTED'
source_spb_module = 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'
train_id = 10000000000


def test_lpd():
    lpd = Detector.getDetector('LPD')
    data, meta = lpd.gen_data(train_id)

    assert len(data) == len(meta) == 1
    assert source_lpd in data
    assert meta[source_lpd]['timestamp.tid'] == train_id
    img = data[source_lpd]['image.data']
    assert img.shape == (16, 256, 256, 300)
    assert not np.any(img[(img<1500) | (img>1600)])


def test_gen():
    agipd = Detector.getDetector('AGIPDModule', gen='zeros', raw=True)
    data, meta = agipd.gen_data(train_id)

    assert len(data) == len(meta) == 1
    assert source_spb_module in data
    assert meta[source_spb_module]['timestamp.tid'] == train_id
    assert data[source_spb_module]['image.data'].shape == (128, 512, 64)
    assert not np.any(data[source_spb_module]['image.data'])


def test_filelike_shape():
    agipd = Detector.getDetector('AGIPDModule', gen='zeros', raw=True, data_like='file')
    data, meta = agipd.gen_data(train_id)
    assert data[source_spb_module]['image.data'].shape == (64, 512, 128)
