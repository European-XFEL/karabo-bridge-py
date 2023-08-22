import queue
from itertools import count
from secrets import token_hex

import zmq
from qtpy.QtCore import QObject, QThread, QTimer, Signal, Slot

from .serializer import deserialize

class Worker(QThread):
    data_queued = Signal()

    def __init__(self, endpoint, sock_type, ctrl_endpoint, queue, stop_after=0,
                 parent=None):
        super().__init__(parent)
        self.endpoint = endpoint
        self.sock_type = sock_type
        self.ctrl_endpoint = ctrl_endpoint
        self.stop_after = stop_after
        self.queue = queue

    def run(self):
        ctx = zmq.Context.instance()
        data_sock = ctx.socket(self.sock_type)
        data_sock.connect(self.endpoint)
        if self.sock_type == zmq.SUB:
            data_sock.setsockopt(zmq.SUBSCRIBE, b'')
        ctrl_sock = ctx.socket(zmq.PULL)
        ctrl_sock.bind(self.ctrl_endpoint)

        poller = zmq.Poller()
        poller.register(data_sock, zmq.POLLIN)
        poller.register(ctrl_sock, zmq.POLLIN)

        if self.sock_type == zmq.REQ:
            data_sock.send(b'next')

        for i in count(start=1):
            ready = [sock for (sock, _) in poller.poll()]
            if ctrl_sock in ready:
                _ = ctrl_sock.recv()
                break


            if data_sock in ready:
                raw_msgs = data_sock.recv_multipart(copy=False)
                data, metadata = deserialize(raw_msgs)
                self.queue.put((data, metadata))
                self.data_queued.emit()
                if (self.stop_after > 0) and (i >= self.stop_after):
                    break

            if self.sock_type == zmq.REQ:
                data_sock.send(b'next')

        # Stop receiving
        ctrl_sock.close()
        data_sock.close()


class QBridgeClient(QObject):
    """Karabo bridge client for use in Qt applications

    Set this up pointing to an endpoint address which is sending Karabo bridge
    data. This is in a format like 'tcp://localhost:45200'.
    Connect to the new_data signal, which is emitted with the data & metadata
    dictionaries for each message received. Then call .start() to receive data,
    either for a set number of trains or until you call .stop().

    This uses a thread, which can cause crashes if you close the application
    while it's still running. You should call .stop() before it is deleted.
    """
    worker = None
    ctrl_endpoint = None
    _dequeuing = False

    new_data = Signal(dict, dict)
    stopped = Signal()

    def __init__(self, endpoint, sock='REQ', parent=None):
        super().__init__(parent)
        self.endpoint = endpoint
        if sock not in {'REQ', 'PULL', 'SUB'}:
            raise ValueError("sock must be 'REQ', 'PULL' or 'SUB'")
        self.sock_type = getattr(zmq, sock)
        self.queue = queue.Queue(maxsize=5)

    def set_endpoint(self, endpoint, sock='REQ'):
        """Change the ZMQ socket to receive data from

        If ``.start()`` was already called, you need to stop & start the client
        again for this to take effect.
        """
        self.endpoint = endpoint
        if sock not in {'REQ', 'PULL', 'SUB'}:
            raise ValueError("sock must be 'REQ', 'PULL' or 'SUB'")
        self.sock_type = getattr(zmq, sock)

    def start(self, stop_after=0):
        """Start receiving data

        Connect to the ``new_data`` signal to handle incoming data.

        If stop_after > 0, it will automatically stop once N trains have been
        received. Otherwise, it continues until ``.stop()`` is called.
        """
        if self.worker is not None:
            raise RuntimeError("QBridgeClient is already running")
        self.ctrl_endpoint = f'inproc://{token_hex(20)}'
        self.worker = worker = Worker(
            self.endpoint, self.sock_type, self.ctrl_endpoint, self.queue,
            stop_after=stop_after, parent=self,
        )
        worker.data_queued.connect(self._start_dequeueing)
        worker.finished.connect(self._worker_finished)
        worker.start()

    @property
    def is_active(self):
        return self.worker is not None

    # Sending received data as signals from the thread causes issues if they
    # are emitted faster than they are processed. This mechanism uses a bounded
    # queue to limit how much data is buffered, and uses QTimer to pull data
    # out of the queue and turn it into signals in cooperation with the event
    # loop. User code should be able to connect to the new_data signal without
    # knowing about this.
    @Slot()
    def _start_dequeueing(self):
        if not self._dequeuing:
            self._dequeuing = True
            QTimer.singleShot(0, self._dequeue_one)

    def _dequeue_one(self):
        try:
            data, metadata = self.queue.get_nowait()
        except queue.Empty:
            self._dequeuing = False
            return

        self.new_data.emit(data, metadata)
        QTimer.singleShot(0, self._dequeue_one)

    def stop(self):
        """Stop receiving data"""
        if self.worker is None:
            return

        ctx = zmq.Context.instance()
        ctrl_sock = ctx.socket(zmq.PUSH)
        ctrl_sock.connect(self.ctrl_endpoint)
        ctrl_sock.send(b'stop')
        ctrl_sock.close()
        # Drain the queue to ensure the worker isn't stuck in .put()
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    def _worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.stopped.emit()
