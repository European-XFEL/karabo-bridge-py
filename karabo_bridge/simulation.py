# coding: utf-8
"""
Set of functions to simulate karabo bridge server and generate fake
detector data.

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>
"""

from functools import partial
from os import uname
import pickle
from time import time
from threading import Thread
import copy

import msgpack
import msgpack_numpy
import numpy as np
import zmq


__all__ = ['start_gen']


msgpack_numpy.patch()


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
    def getDetector(detector, source='', raw=False, gen='random'):
        if detector == 'AGIPD':
            if not raw:
                default = 'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED'
            else:
                default = 'SPB_DET_AGIPD1M-1/CAL/APPEND_RAW'
            source = source or default
            return AGIPD(source, raw=raw, gen=gen)
        elif detector == 'AGIPDModule':
            if not raw:
                raise NotImplementedError(
                    'Calib. Data for single Modules not available yet')
            source = source or 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf'
            return AGIPDModule(source, raw=raw, gen=gen)
        elif detector == 'LPD':
            if not raw:
                default = 'FXE_DET_LPD1M-1/CAL/APPEND_CORRECTED'
            else:
                default = 'FXE_DET_LPD1M-1/CAL/APPEND_RAW'
            source = source or default
            return LPD(source, raw=raw, gen=gen)
        else:
            raise NotImplementedError('detector %r not available' % detector)

    def __init__(self, source='', raw=True, gen='random'):
        self.source = source or 'INST_DET_GENERIC/DET/detector'
        self.raw = raw
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
        if self.modules == 1:
            return (self.mod_y, self.mod_x, self.pulses)
        else:
            return (self.modules, self.mod_y, self.mod_x, self.pulses)

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


def generate(detector, nsources):
    tid_counter = 10000000000
    while True:
        data, meta = detector.gen_data(tid_counter)

        if nsources > 1:
            source = detector.source
            for i in range(nsources):
                src = source + "-" + str(i+1)
                data[src] = copy.deepcopy(data[source])
                meta[src] = copy.deepcopy(meta[source])
                meta[src]['source'] = src
            del data[source]
            del meta[source]

        tid_counter += 1
        yield (data, meta)


def containize(train_data, ser, ser_func, vers):
    data, meta = train_data

    if vers not in ('1.0', '2.0', '2.1', '2.2'):
        raise ValueError("Invalid version %s" % vers)

    if vers in ('1.0', '2.0'):
        for key, value in meta.items():
            data[key].update({'metadata': value})

        if vers == '1.0':
            return [ser_func(data)]

    elif vers == '2.1':
        for key, value in meta.items():
            m = {}
            for mkey, mval in value.items():
                m['metadata.'+mkey] = mval
            data[key].update(m)

    newdata = {}
    for src, props in data.items():
        arr = {}
        arr_keys = []
        for key, value in props.items():
            if isinstance(value, np.ndarray):
                arr[key] = props[key]
                arr_keys.append(key)
        for arr_key in arr_keys:
            data[src].pop(arr_key)
        newdata[src] = (data[src], arr, meta[src])

    msg = []
    for src, (dic, arr, src_metadata) in newdata.items():
        header = {'source': src, 'content': str(ser)}
        if vers == '2.2':
            header['metadata'] = src_metadata
        msg.append(ser_func(header))
        msg.append(ser_func(dic))

        for path, array in arr.items():
            header = {'source': src, 'content': 'array', 'path': path,
                      'dtype': str(array.dtype), 'shape': array.shape}
            msg.append(ser_func(header))
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            msg.append(memoryview(array))

    return msg


TIMING_INTERVAL = 50


def start_gen(port, ser='msgpack', version='2.2', detector='AGIPD',
              raw=False, nsources=1, datagen='random', *,
              debug=True):
    """"Karabo bridge server simulation.

    Simulate a Karabo Bridge server and send random data from a detector,
    either AGIPD or LPD.

    Parameters
    ----------
    port: str
        The port to on which the server is bound.
    ser: str, optional
        The serialization algorithm, default is msgpack.
    version: str, optional
        The container version of the serialized data.
    detector: str, optional
        The data format to send, default is AGIPD detector.
    raw: bool, optional
        Generate raw data output if True, else CORRECTED. Default is False.
    nsources: int, optional
        Number of sources.
    datagen: string, optional
        Generator function used to generate detector data. Default is random.
    """
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.bind('tcp://*:{}'.format(port))

    if ser != 'msgpack':
        raise ValueError("Unknown serialisation format %s" % ser)
    serialize = partial(msgpack.dumps, use_bin_type=True)
    det = Detector.getDetector(detector, raw=raw, gen=datagen)
    generator = generate(det, nsources)

    print('Simulated Karabo-bridge server started on:\ntcp://{}:{}'.format(
          uname().nodename, port))

    t_prev = time()
    n = 0

    try:
        while True:
            msg = socket.recv()
            if msg == b'next':
                train = next(generator)
                msg = containize(train, ser, serialize, version)
                socket.send_multipart(msg, copy=False)
                if debug:
                    print('Server : emitted train:',
                          train[1][list(train[1].keys())[0]]['timestamp.tid'])
                n += 1
                if n % TIMING_INTERVAL == 0:
                    t_now = time()
                    print('Sent {} trains in {:.2f} seconds ({:.2f} Hz)'
                          ''.format(TIMING_INTERVAL, t_now - t_prev,
                                    TIMING_INTERVAL / (t_now - t_prev)))
                    t_prev = t_now
            else:
                print('wrong request')
                break
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        socket.close()
        context.destroy()


class ServeInThread(Thread):
    def __init__(self, endpoint, ser='msgpack', protocol_version='2.2',
                 detector='AGIPD', raw=False, nsources=1,
                 datagen='random'):
        super().__init__()
        self.protocol_version = protocol_version

        self.serialization_fmt = ser
        if ser != 'msgpack':
            raise ValueError("Unknown serialisation format %s" % ser)
        self.serialize = partial(msgpack.dumps, use_bin_type=True)

        det = Detector.getDetector(detector, raw=raw, gen=datagen)
        self.generator = generate(det, nsources)

        self.zmq_context = zmq.Context()
        self.server_socket = self.zmq_context.socket(zmq.REP)
        self.server_socket.setsockopt(zmq.LINGER, 0)
        self.server_socket.bind(endpoint)

        self.stopper_r = self.zmq_context.socket(zmq.PAIR)
        self.stopper_r.bind('inproc://sim-server-stop')
        self.stopper_w = self.zmq_context.socket(zmq.PAIR)
        self.stopper_w.connect('inproc://sim-server-stop')

    def run(self):
        poller = zmq.Poller()
        poller.register(self.server_socket, zmq.POLLIN)
        poller.register(self.stopper_r, zmq.POLLIN)
        while True:
            events = dict(poller.poll())
            if self.server_socket in events:
                msg = self.server_socket.recv()
                if msg == b'next':
                    train = next(self.generator)
                    msg = containize(train, self.serialization_fmt,
                                     self.serialize, self.protocol_version)
                    self.server_socket.send_multipart(msg, copy=False)
                else:
                    print('Unrecognised request:', msg)
            elif self.stopper_r in events:
                self.stopper_r.recv()
                break

    def stop(self):
        self.stopper_w.send(b'')
        self.join()
        self.zmq_context.destroy()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
