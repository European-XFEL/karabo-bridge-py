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


DETECTORS = {
    'AGIPD': {
        'source': 'SPB_DET_AGIPD1M-1/DET/detector',
        'pulses': 64,
        'modules': 16,
        'module_shape': (128, 512),  # (y, x)
    },
    'LPD': {
        'source': 'FXE_DET_LPD1M-1/DET/detector',
        'pulses': 300,
        'modules': 16,
        'module_shape': (256, 256),  # (y, x)
    }
}


def gen_combined_detector_data(detector_info, tid_counter, corrected=False,
                               nsources=1):
    source = detector_info['source']
    gen = {source: {}}
    meta = {}

    # metadata
    ts = time()
    sec, frac = str(ts).split('.')
    meta[source] = {
        'source': source,
        'timestamp': ts,
        'timestamp.tid': tid_counter,
        'timestamp.sec': sec,
        'timestamp.frac': frac.ljust(18, '0')  # attosecond resolution
    }

    pulse_count = detector_info['pulses']
    array_shape = tuple((detector_info['modules'], ) +
                        detector_info['module_shape'] + (pulse_count, ))

    # detector random data
    if corrected:
        gain_data = np.zeros(array_shape, dtype=np.uint16)
        domain = detector_info['source'].partition('/')[0]
        passport = [
            '%s/CAL/THRESHOLDING_Q1M1' % domain,
            '%s/CAL/OFFSET_CORR_Q1M1' % domain,
            '%s/CAL/RELGAIN_CORR_Q1M1' % domain
        ]

        gen[source]['image.gain'] = gain_data
        gen[source]['image.passport'] = passport

    rand_data = partial(np.random.uniform, low=1500, high=1600,
                        size=detector_info['module_shape'])
    if corrected:
        data = np.zeros(array_shape, dtype=np.float32)
    else:
        data = np.zeros(array_shape, dtype=np.uint16)
    for pulse in range(pulse_count):
        for module in range(detector_info['modules']):
            data[module, :, :, pulse] = rand_data()
    cellId = np.array([i for i in range(pulse_count)], dtype=np.uint16)
    length = np.ones(pulse_count, dtype=np.uint32) * int(131072)
    pulseId = np.array([i for i in range(pulse_count)], dtype=np.uint64)
    trainId = np.ones(pulse_count, dtype=np.uint64) * int(tid_counter)
    status = np.zeros(pulse_count, dtype=np.uint16)

    gen[source]['image.data'] = data
    gen[source]['image.cellId'] = cellId
    gen[source]['image.length'] = length
    gen[source]['image.pulseId'] = pulseId
    gen[source]['image.trainId'] = trainId
    gen[source]['image.status'] = status

    checksum = bytes(np.ones(16, dtype=np.int8))
    magicNumberEnd = bytes(np.ones(8, dtype=np.int8))
    status = 0

    gen[source]['trailer.checksum'] = checksum
    gen[source]['trailer.magicNumberEnd'] = magicNumberEnd
    gen[source]['trailer.status'] = status

    data = bytes(np.ones(416, dtype=np.uint8))

    gen[source]['detector.data'] = data

    dataId = 0
    linkId = np.iinfo(np.uint64).max
    magicNumberBegin = bytes(np.ones(8, dtype=np.int8))
    majorTrainFormatVersion = 2
    minorTrainFormatVersion = 1
    reserved = bytes(np.ones(16, dtype=np.uint8))

    gen[source]['header.dataId'] = dataId
    gen[source]['header.linkId'] = linkId
    gen[source]['header.magicNumberBegin'] = magicNumberBegin
    gen[source]['header.majorTrainFormatVersion'] = majorTrainFormatVersion
    gen[source]['header.minorTrainFormatVersion'] = minorTrainFormatVersion
    gen[source]['header.pulseCount'] = pulse_count
    gen[source]['header.reserved'] = reserved
    gen[source]['header.trainId'] = tid_counter

    if nsources > 1:
        for i in range(nsources):
            src = source + "-" + str(i+1)
            gen[src] = copy.deepcopy(gen[source])
            meta[src] = copy.deepcopy(gen[source])
            meta[src]['source'] = src

        del gen[source]
        del meta[source]

    return gen, meta


def generate(detector_info, corrected, nsources):
    tid_counter = 10000000000
    while True:
        data, meta = gen_combined_detector_data(detector_info, tid_counter,
                                                corrected=corrected,
                                                nsources=nsources)
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


def start_gen(port, ser='msgpack', version='2.2', detector='AGIPD',
              corrected=True, nsources=1, *, debug=True):
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
    corrected: bool, optional
        Generate corrected data output if True, else RAW. Default is True.
    nsources: int, optional
        Number of sources.
    """
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.setsockopt(zmq.LINGER, 0)
    socket.bind('tcp://*:{}'.format(port))

    if ser == 'msgpack':
        serialize = partial(msgpack.dumps, use_bin_type=True)
    elif ser == 'pickle':
        serialize = pickle.dumps
    else:
        raise ValueError("Unknown serialisation format %s" % ser)

    detector_info = DETECTORS[detector]
    generator = generate(detector_info, corrected, nsources)

    print('Simulated Karabo-bridge server started on:\ntcp://{}:{}'.format(
          uname().nodename, port))

    try:
        while True:
            msg = socket.recv()
            if msg == b'next':
                train = next(generator)
                msg = containize(train, ser, serialize, version)
                socket.send_multipart(msg)
                if debug:
                    print('Server : emitted train:',
                          train[1][list(train[1].keys())[0]]['timestamp.tid'])
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
                 detector='AGIPD', corrected=True, nsources=1):
        super().__init__()
        self.protocol_version = protocol_version

        self.serialization_fmt = ser
        if ser == 'msgpack':
            self.serialize = partial(msgpack.dumps, use_bin_type=True)
        elif ser == 'pickle':
            self.serialize = pickle.dumps
        else:
            raise ValueError("Unknown serialisation format %s" % ser)

        detector_info = DETECTORS[detector]

        self.generator = generate(detector_info, corrected, nsources)

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
                    self.server_socket.send_multipart(msg)
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
