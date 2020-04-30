from functools import partial
from queue import Queue
from socket import gethostname
from threading import Thread
from time import time

import zmq

from .serializer import serialize
from .simulation import data_generator


__all__ = ['ServerInThread', 'start_gen']


class Sender:
    def __init__(self, endpoint, sock='REP', protocol_version='2.2',
                 dummy_timestamps=False):
        self.dump = partial(serialize, protocol_version=protocol_version,
                            dummy_timestamps=dummy_timestamps)
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

        self.poller = zmq.Poller()
        self.poller.register(self.server_socket, zmq.POLLIN | zmq.POLLOUT)
        self.poller.register(self.stopper_r, zmq.POLLIN)

    @property
    def endpoint(self):
        endpoint = self.server_socket.getsockopt_string(zmq.LAST_ENDPOINT)
        endpoint = endpoint.replace('0.0.0.0', gethostname())
        return endpoint

    def send(self, data, metadata=None):
        payload = self.dump(data, metadata)
        events = dict(self.poller.poll())

        if self.stopper_r in events:
            self.stopper_r.recv()
            return True

        if events[self.server_socket] is zmq.POLLIN:
            msg = self.server_socket.recv()
            if msg != b'next':
                print(f'Unrecognised request: {msg}')
                self.server_socket.send(b'Error: bad request %b' % msg)
                return

        self.server_socket.send_multipart(payload, copy=False)


class SimServer(Sender):
    def __init__(self, endpoint, sock='REP', ser='msgpack',
                 protocol_version='2.2', detector='AGIPD', raw=False,
                 nsources=1, datagen='random', data_like='online', *,
                 debug=True):
        super().__init__(endpoint, sock=sock, protocol_version=protocol_version)

        if ser != 'msgpack':
            raise ValueError("Unknown serialisation format %s" % ser)

        self.data = data_generator(
            detector=detector, raw=raw, nsources=nsources, datagen=datagen,
            data_like=data_like, debug=debug)
        self.debug = debug

    def loop(self):
        print(f'Simulated Karabo-bridge server started on:\n'
              f'tcp://{self.endpoint}')

        timing_interval = 50
        t_prev = time()
        n = 0

        for data, meta in self.data:
            done = self.send(data, meta)
            if done:
                break

            if self.debug:
                print('Server : emitted train:',
                      next(v for v in meta.values())['timestamp.tid'])
            n += 1
            if n % timing_interval == 0:
                t_now = time()
                print('Sent {} trains in {:.2f} seconds ({:.2f} Hz)'
                      ''.format(timing_interval, t_now - t_prev,
                                timing_interval / (t_now - t_prev)))
                t_prev = t_now


class ServerInThread(Sender):
    def __init__(self, endpoint, sock='REP', maxlen=10, protocol_version='2.2',
                 dummy_timestamps=False):
        """ZeroMQ interface sending data over a TCP socket.

        example::

            # Server:
            serve = ServerInThread(1234)
            serve.start()

            for tid, data in run.trains():
                result = important_processing(data)
                serve.feed(result)

            # Client:
            from karabo_bridge import Client
            client = Client('tcp://server.hostname:1234')
            data = client.next()

        Parameters
        ----------
        endpoint: str
            The address string.
        sock: str
            socket type - supported: REP, PUB, PUSH (default REP).
        maxlen: int, optional
            How many trains to cache before sending (default: 10)
        protocol_version: ('1.0' | '2.1')
            Which version of the bridge protocol to use. Defaults to the latest
            version implemented.
        dummy_timestamps: bool
            Some tools (such as OnDA) expect the timestamp information to be in
            the messages. We can't give accurate timestamps where these are not
            in the file, so this option generates fake timestamps from the time
            the data is fed in.
        """
        super().__init__(endpoint, sock=sock, protocol_version=protocol_version,
                         dummy_timestamps=dummy_timestamps)
        self.thread = Thread(target=self._run, daemon=True)
        self.buffer = Queue(maxsize=maxlen)

    def feed(self, data, metadata=None, block=True, timeout=None):
        """Push data to the sending queue.

        This blocks if the queue already has *maxlen* items waiting to be sent.

        Parameters
        ----------
        data : dict
            Contains train data. The dictionary has to follow the karabo_bridge
            see :func:`~karabo_bridge.serializer.serialize` for details

        metadata : dict, optional
            Contains train metadata. If the metadata dict is not provided it
            will be extracted from 'data' or an empty dict if 'metadata' key
            is missing from a data source.
            see :func:`~karabo_bridge.serializer.serialize` for details

        block: bool
            If True, block if necessary until a free slot is available or
            'timeout' has expired. If False and there is no free slot, raises
            'queue.Full' (timeout is ignored)

        timeout: float
            In seconds, raises 'queue.Full' if no free slow was available
            within that time.
        """
        self.buffer.put((data, metadata), block=block, timeout=timeout)

    def _run(self):
        while True:
            done = self.send(*self.buffer.get())
            if done:
                break

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopper_w.send(b'')
        if self.buffer.qsize() == 0:
            self.buffer.put(({},))  # release blocking queue
        self.thread.join()
        self.zmq_context.destroy(linger=0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class SimServerInThread(SimServer, ServerInThread):
    def _run(self):
        self.loop()


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
    sender = SimServer(
        endpoint, sock=sock, ser=ser, protocol_version=version,
        detector=detector, raw=raw, nsources=nsources, datagen=datagen,
        data_like=data_like, debug=debug
    )
    try:
        sender.loop()
    except KeyboardInterrupt:
        pass
    print('\nStopped.')
