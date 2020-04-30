# coding: utf-8
"""
Set of functions to simulate karabo bridge server and generate fake
detector data.

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>
"""

import copy
from itertools import count
from time import time

import numpy as np


class Detector:
    # Overridden in subclasses
    pulses = 0  # nimages per XRAY train
    modules = 0  # nb of super modules composing the detector
    mod_x = 0  # pixel count (y axis) of a single super module
    mod_y = 0  # pixel count (x axis) of a single super module
    pixel_size = 0  # [mm]
    distance = 0  # Sample to detector distance [mm]
    layout = np.array([[]])  # super module layout of the detector

    @staticmethod
    def getDetector(detector, source='', raw=False, gen='random',
                    data_like='online'):
        if detector == 'AGIPD':
            if not raw:
                default = 'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
            else:
                default = 'SPB_DET_AGIPD1M-1/CAL/APPEND_RAW'
            source = source or default
            return AGIPD(source, raw=raw, gen=gen, data_like=data_like)
        elif detector == 'AGIPDModule':
            if not raw:
                raise NotImplementedError(
                    'Calib. Data for single Modules not available yet')
            source = source or 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'
            return AGIPDModule(source, raw=raw, gen=gen, data_like=data_like)
        elif detector == 'LPD':
            if not raw:
                default = 'FXE_DET_LPD1M-1/CAL/APPEND_CORRECTED'
            else:
                default = 'FXE_DET_LPD1M-1/CAL/APPEND_RAW'
            source = source or default
            return LPD(source, raw=raw, gen=gen)
        else:
            raise NotImplementedError('detector %r not available' % detector)

    def __init__(self, source='', raw=True, gen='random', data_like='online'):
        self.source = source or 'INST_DET_GENERIC/DET/detector'
        self.raw = raw
        self.data_like = data_like
        if gen == 'random':
            self.genfunc = self.random
        elif gen == 'zeros':
            self.genfunc = self.zeros
        else:
            raise NotImplementedError('gen func %r not implemented' % gen)

    @property
    def data_type(self):
        if self.raw:
            return np.uint16
        else:
            return np.float32

    def corr_passport(self):
        domain = self.source.partition('/')[0]
        passport = [
            '%s/CAL/THRESHOLDING_Q1M1' % domain,
            '%s/CAL/OFFSET_CORR_Q1M1' % domain,
            '%s/CAL/RELGAIN_CORR_Q1M1' % domain
        ]
        return passport

    @property
    def data_shape(self):
        shape = () if self.modules == 1 else (self.modules, )
        if self.data_like == 'online':
            shape += (self.mod_y, self.mod_x, self.pulses)
        else:
            shape = (self.pulses, ) + shape + (self.mod_x, self.mod_y)
        return shape

    def random(self):
        return np.random.uniform(low=1500, high=1600,
                                 size=self.data_shape).astype(self.data_type)

    def zeros(self):
        return np.zeros(self.data_shape, dtype=self.data_type)

    def module_position(self, ix):
        y, x = np.where(self.layout == ix)
        assert len(y) == len(x) == 1
        return x[0], y[0]

    @staticmethod
    def gen_metadata(source, timestamp, trainId):
        sec, frac = str(timestamp).split('.')
        meta = {}
        meta[source] = {
            'source': source,
            'timestamp': timestamp,
            'timestamp.tid': trainId,
            'timestamp.sec': sec,
            'timestamp.frac': frac.ljust(18, '0')  # attosecond resolution
        }
        return meta

    def gen_data(self, trainId):
        data = {}
        timestamp = time()
        data['image.data'] = self.genfunc()
        base_src = '/'.join((self.source.rpartition('/')[0], '{}CH0:xtdf'))
        sources = [base_src.format(i) for i in range(16)]
        # TODO: cellId differ between AGIPD/LPD
        data['image.cellId'] = np.arange(self.pulses, dtype=np.uint16)
        if not self.raw:
            data['image.passport'] = self.corr_passport()
        if self.modules > 1:
            # More than one modules have sources
            data['sources'] = sources
            data['modulesPresent'] = [True for i in range(self.modules)]
        # Image gain has only entries for one module
        data['image.gain'] = np.zeros((self.mod_y, self.mod_x, self.pulses),
                                      dtype=np.uint16)
        # TODO: pulseId differ between AGIPD/LPD
        data['image.pulseId'] = np.arange(self.pulses, dtype=np.uint64)
        data['image.trainId'] = (
            np.ones(self.pulses) * trainId).astype(np.uint64)

        meta = self.gen_metadata(self.source, timestamp, trainId)
        return {self.source: data}, meta


class AGIPDModule(Detector):
    pulses = 64
    modules = 1
    mod_y = 128
    mod_x = 512
    pixel_size = 0.2
    distance = 2000
    layout = np.array([
        [12, 0],
        [13, 1],
        [14, 2],
        [15, 3],
        [8, 4],
        [9, 5],
        [10, 6],
        [11, 7],
    ])


class AGIPD(AGIPDModule):
    modules = 16


class LPD(Detector):
    pulses = 300
    modules = 16
    mod_y = 256
    mod_x = 256
    pixel_size = 0.5
    distance = 275
    layout = np.array([
        [15, 12, 3, 0],
        [14, 13, 2, 1],
        [11, 8, 7, 4],
        [10, 9, 6, 5],
    ])


def data_generator(detector='AGIPD', raw=False, nsources=1, datagen='random',
                   data_like='online', *, debug=False):

    detector = Detector.getDetector(detector, raw=raw, gen=datagen,
                                    data_like=data_like)

    for train_id in count(start=10000000000):
        data, meta = detector.gen_data(train_id)

        if nsources > 1:
            source = detector.source
            for i in range(nsources):
                src = source + "-" + str(i+1)
                data[src] = copy.deepcopy(data[source])
                meta[src] = copy.deepcopy(meta[source])
                meta[src]['source'] = src
            del data[source]
            del meta[source]

        yield (data, meta)
