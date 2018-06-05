# coding: utf-8
"""
Set of functions to simulate karabo bridge server and generate fake
detector data.

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>
"""

from collections import deque
from functools import partial
import pickle
from time import sleep, time
from threading import Thread
import copy

import msgpack
import msgpack_numpy
import numpy as np
import zmq


__all__ = ['start_gen']


msgpack_numpy.patch()


# AGIPD
_PULSES = 32
_MODULES = 16
_MOD_X = 512
_MOD_Y = 128
_SHAPE = (_PULSES, _MODULES, _MOD_X, _MOD_Y)


# LPD
# _PULSES = 32
# _MODULES = 16
# _MOD_X = 256
# _MOD_Y = 256
# _SHAPE = (_PULSES, _MODULES, _MOD_X, _MOD_Y)


def gen_combined_detector_data(source, tid_counter, corrected=False, nsources=1):
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

    # detector random data
    if corrected:
        global _PULSES
        _PULSES = 31
        global _SHAPE
        _SHAPE = (_PULSES, _MODULES, _MOD_X, _MOD_Y)

        gain_data = np.zeros(_SHAPE, dtype=np.uint16)
        passport = [
            'SPB_DET_AGIPD1M-1/CAL/THRESHOLDING_Q3M2',
            'SPB_DET_AGIPD1M-1/CAL/OFFSET_CORR_Q3M2',
            'SPB_DET_AGIPD1M-1/CAL/RELGAIN_CORR_Q3M2'
        ]

        gen[source]['image.gain'] = gain_data
        gen[source]['image.passport'] = passport

    rand_data = partial(np.random.uniform, low=1500, high=1600,
                        size=(_MOD_X, _MOD_Y))
    data = np.zeros(_SHAPE, dtype=np.uint16)  # np.float32)
    for pulse in range(_PULSES):
        for module in range(_MODULES):
            data[pulse, module, ] = rand_data()
    cellId = np.array([i for i in range(_PULSES)], dtype=np.uint16)
    length = np.ones(_PULSES, dtype=np.uint32) * int(131072)
    pulseId = np.array([i for i in range(_PULSES)], dtype=np.uint64)
    trainId = np.ones(_PULSES, dtype=np.uint64) * int(tid_counter)
    status = np.zeros(_PULSES, dtype=np.uint16)

    gen[source]['image.data'] = data
    gen[source]['image.cellId'] = cellId
    gen[source]['image.length'] = length
    gen[source]['image.pulseId'] = pulseId
    gen[source]['image.trainId'] = trainId
    gen[source]['image.status'] = status

    checksum = bytes(np.ones(16, dtype=np.int8))
    magicNumberEnd = bytes(np.ones(8, dtype=np.int8))
    status = 0
    trainId = tid_counter

    gen[source]['trailer.checksum'] = checksum
    gen[source]['trailer.magicNumberEnd'] = magicNumberEnd
    gen[source]['trailer.status'] = status

    data = bytes(np.ones(416, dtype=np.uint8))
    trainId = tid_counter

    gen[source]['detector.data'] = data

    dataId = 0
    linkId = np.iinfo(np.uint64).max
    magicNumberBegin = bytes(np.ones(8, dtype=np.int8))
    majorTrainFormatVersion = 2
    minorTrainFormatVersion = 1
    pulseCount = _PULSES
    reserved = bytes(np.ones(16, dtype=np.uint8))
    trainId = tid_counter

    gen[source]['header.dataId'] = dataId
    gen[source]['header.linkId'] = linkId
    gen[source]['header.magicNumberBegin'] = magicNumberBegin
    gen[source]['header.majorTrainFormatVersion'] = majorTrainFormatVersion
    gen[source]['header.minorTrainFormatVersion'] = minorTrainFormatVersion
    gen[source]['header.pulseCount'] = pulseCount
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


def generate(source, corrected, queue, nsources):
    tid_counter = 10000000000
    try:
        while True:
            if len(queue) < queue.maxlen:
                data, meta = gen_combined_detector_data(source, tid_counter,
                                                        corrected=corrected,
                                                        nsources=nsources)
                tid_counter += 1
                queue.append((data, meta))
                print('Server : buffered train:',
                      meta[list(meta.keys())[0]]['timestamp.tid'])
            else:
                sleep(0.1)
    except KeyboardInterrupt:
        return


def set_detector_params(det):
    if det == 'LPD':
        global _MOD_X
        _MOD_X = 256
        global _MOD_Y
        _MOD_Y = 256
        return 'FXE_DET_LPD1M-1/DET/detector'
    else:
        return 'SPB_DET_AGIPD1M-1/DET/detector'


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
        newdata[src] = (data[src], arr, {})  # the last item is ImageData objects.

    msg = []
    for src, (dic, arr, img) in newdata.items():
        header = {'source': src, 'content': str(ser)}
        msg.append(ser_func(header))
        msg.append(ser_func(dic))

        for path, array in arr.items():
            header = {'source': src, 'content': 'array', 'path': path,
                      'dtype': str(array.dtype), 'shape': array.shape}
            msg.append(ser_func(header))
            if not array.flags['C_CONTIGUOUS']:
                array = np.ascontiguousarray(array)
            msg.append(memoryview(array))

        for path, image in img.items():
            # TODO
            continue

    return msg


def start_gen(port, ser='msgpack', version='2.2', detector='AGIPD',
              corrected=True, nsources=1):
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

    source = set_detector_params(detector)

    if ser == 'msgpack':
        serialize = partial(msgpack.dumps, use_bin_type=True)
    elif ser == 'pickle':
        serialize = pickle.dumps
    else:
        raise ValueError("Unknown serialisation format %s" % ser)

    queue = deque(maxlen=10)

    t = Thread(target=generate, args=(source, corrected, queue, nsources, ))
    t.daemon = True
    t.start()

    try:
        while True:
            msg = socket.recv()
            if msg == b'next':
                while len(queue) <= 0:
                    sleep(0.1)

                train = queue.popleft()
                msg = containize(train, ser, serialize, version)
                socket.send_multipart(msg)
            else:
                print('wrong request')
                break
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        socket.close()
        context.destroy()
