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
from socket import gethostname
from time import time
from threading import Thread

import numpy as np
import zmq

from .serializer import serialize


__all__ = ['start_gen']


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


TIMING_INTERVAL = 50


class Sender:
    def __init__(self, endpoint, sock='REP', ser='msgpack',
                 protocol_version='2.2', detector='AGIPD', raw=False,
                 nsources=1, datagen='random', data_like='online', *,
                 debug=True):
        if ser != 'msgpack':
            raise ValueError("Unknown serialisation format %s" % ser)
        self.protocol_version = protocol_version

        det = Detector.getDetector(detector, raw=raw, gen=datagen,
                                   data_like=data_like)
        self.generator = generate(det, nsources)

        self.zmq_context = zmq.Context()
        if sock == 'REP':
            self.server_socket = self.zmq_context.socket(zmq.REP)
        elif sock == 'PUB':
            self.server_socket = self.zmq_context.socket(zmq.PUB)
        elif sock == 'PUSH':
            self.server_socket = self.zmq_context.socket(zmq.PUSH)
        else:
            raise ValueError(f'Unsupported socket type: {sock}')
        self.server_socket.setsockopt(zmq.LINGER, 0)
        self.server_socket.set_hwm(1)
        self.server_socket.bind(endpoint)

        self.stopper_r = self.zmq_context.socket(zmq.PAIR)
        self.stopper_r.bind('inproc://sim-server-stop')
        self.stopper_w = self.zmq_context.socket(zmq.PAIR)
        self.stopper_w.connect('inproc://sim-server-stop')

        self.debug = debug

    def loop(self):
        poller = zmq.Poller()
        poller.register(self.server_socket, zmq.POLLIN | zmq.POLLOUT)
        poller.register(self.stopper_r, zmq.POLLIN)

        endpoint = self.server_socket.getsockopt_string(zmq.LAST_ENDPOINT)
        port = endpoint.rpartition(':')[-1]
        print(f'Simulated Karabo-bridge server started on:\n'
              f'tcp://{gethostname()}:{port}')

        t_prev = time()
        n = 0

        while True:
            data, meta = next(self.generator)
            payload = serialize(data, meta,
                                protocol_version=self.protocol_version)

            events = dict(poller.poll())

            if self.stopper_r in events:
                self.stopper_r.recv()
                break
            if events[self.server_socket] is zmq.POLLIN:
                msg = self.server_socket.recv()
                if msg != b'next':
                    print(f'Unrecognised request: {msg}')
                    self.server_socket.send(b'Error: bad request %b' % msg)
                    continue

            self.server_socket.send_multipart(payload, copy=False)

            if self.debug:
                print('Server : emitted train:',
                      next(v for v in meta.values())['timestamp.tid'])
            n += 1
            if n % TIMING_INTERVAL == 0:
                t_now = time()
                print('Sent {} trains in {:.2f} seconds ({:.2f} Hz)'
                      ''.format(TIMING_INTERVAL, t_now - t_prev,
                                TIMING_INTERVAL / (t_now - t_prev)))
                t_prev = t_now


def start_gen(port, sock='REP', ser='msgpack', version='2.2', detector='AGIPD',
              raw=False, nsources=1, datagen='random', data_like='online', *,
              debug=True):
    """Karabo bridge server simulation.

    Simulate a Karabo Bridge server and send random data from a detector,
    either AGIPD or LPD.

    Parameters
    ----------
    port: str
        The port to on which the server is bound.
    sock: str, optional
        socket type - supported: REP, PUB, PUSH. Default is REP.
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
    data_like: string optional ['online', 'file']
        Data array axes ordering for Mhz detector.
        The data arrays's axes can have different ordering on online data. The
        calibration processing orders axes as (fs, ss, pulses), whereas
        data in files have (pulses, ss, fs).
        This option allow to chose between 2 ordering:
        - online: (modules, fs, ss, pulses)
        - file: (pulses, modules, ss, fs)
        Note that the real system can send data in both shape with a
        performance penalty for the file-like array shape.

        Default is online.
    """
    endpoint = f'tcp://*:{port}'
    sender = Sender(
        endpoint, sock=sock, ser=ser, protocol_version=version,
        detector=detector, raw=raw, nsources=nsources, datagen=datagen,
        data_like=data_like, debug=debug
    )
    try:
        sender.loop()
    except KeyboardInterrupt:
        pass
    print('\nStopped.')


class ServeInThread(Thread):
    def __init__(self, endpoint, sock='REP', ser='msgpack',
                 protocol_version='2.2', detector='AGIPD', raw=False,
                 nsources=1, datagen='random', data_like='online', *,
                 debug=True):
        super().__init__()

        self.sender = Sender(
            endpoint, sock=sock, ser=ser, protocol_version=protocol_version,
            detector=detector, raw=raw, nsources=nsources, datagen=datagen,
            data_like=data_like, debug=debug
        )

    def run(self):
        self.sender.loop()

    def stop(self):
        self.sender.stopper_w.send(b'')
        self.join()
        self.sender.zmq_context.destroy(linger=0)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
