import numpy as np

from karabo_bridge.simulation import Detector


source_lpd = 'FXE_DET_LPD1M-1/DET/detector'
source_spb = 'SPB_DET_AGIPD1M-1/DET/detector'
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
    agipd = Detector.getDetector('AGIPD', gen='zeros')
    data, meta = agipd.gen_data(train_id)

    assert len(data) == len(meta) == 1
    assert source_spb in data
    assert meta[source_spb]['timestamp.tid'] == train_id
    assert data[source_spb]['image.data'].shape == (16, 128, 512, 64)
    assert not np.any(data[source_spb]['image.data'])
