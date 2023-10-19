# coding: utf-8
"""
Karabo bridge client.

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>
"""

import zmq

from .serializer import deserialize


__all__ = ['Client']


class Client:
    """Karabo bridge client for Karabo pipeline data.

    This class can request data to a Karabo bridge server.
    Create the client with::

        from karabo_bridge import Client
        krb_client = Client("tcp://153.0.55.21:12345")

    then call ``data = krb_client.next()`` to request next available data
    container.

    Parameters
    ----------
    endpoints : str or Iterable
        server socket(s) you want to connect to (only support TCP socket).
    sock : str, optional
        socket type - supported: REQ, SUB.
    ser : str, DEPRECATED
        Serialization protocol to use to decode the incoming message (default
        is msgpack) - supported: msgpack.
    context : zmq.Context
        To run the Client's sockets using a provided ZeroMQ context.
    timeout : int
        Timeout on :meth:`next` (in seconds)

        Data transfered at the EuXFEL for Mega-pixels detectors can be very
        large. Setting a too small timeout might end in never getting data.
        Some example of transfer timing for 1Mpix detector (AGIPD, LPD):

           - 32 pulses per train (125 MB): ~0.1 s
           - 128 pulses per train (500 MB): ~0.4 s
           - 350 pulses per train (1.37 GB): ~1 s

    Raises
    ------
    NotImplementedError
        if socket type or serialization algorithm is not supported.
    ZMQError
        if provided endpoint is not valid.
    """
    def __init__(self, endpoints, sock='REQ', ser='msgpack', timeout=None,
                 context=None):

        if ser != 'msgpack':
            raise Exception('Only serialization supported is msgpack')

        self._context = context or zmq.Context()
        self._socket = None

        if sock == 'PULL':
            self._socket = self._context.socket(zmq.PULL)
        elif sock == 'REQ':
            self._socket = self._context.socket(zmq.REQ)
        elif sock == 'SUB':
            self._socket = self._context.socket(zmq.SUB)
            self._socket.setsockopt(zmq.SUBSCRIBE, b'')
        elif sock == 'DEALER':
            self._socket = self._context.socket(zmq.DEALER)
        else:
            raise NotImplementedError('Unsupported socket: %s' % str(sock))
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.set_hwm(1)

        if isinstance(endpoints, str):
            endpoints = [endpoints]

        self._num_endpoints = len(endpoints)

        if self._num_endpoints > 1 and self._socket.type != zmq.DEALER:
            raise ValueError('multiple endpoints only supported with DEALER '
                             'sockets')

        for endpoint in endpoints:
            self._socket.connect(endpoint)

        if timeout is not None:
            self._socket.setsockopt(zmq.RCVTIMEO, int(timeout * 1000))
        self._recv_ready = False

        self._pattern = self._socket.type

    def next(self, divisor=None, remainder=None):
        """Request next data container.

        This function call is blocking.

        Returns
        -------
        data : dict
            The data for this train, keyed by source name.
        meta : dict
            The metadata for this train, keyed by source name.

            This dictionary is populated for protocol version 1.0 and 2.2.
            For other protocol versions, metadata information is available in
            `data` dict.

        Raises
        ------
        TimeoutError
            If timeout is reached before receiving data.
        """

        recv_slice = slice(None)

        if self._pattern in {zmq.REQ, zmq.DEALER} and not self._recv_ready:
            if divisor is not None and remainder is not None:
                msg = f'next {divisor} {remainder}'.encode('ascii')
            else:
                msg = b'next'

            if self._pattern == zmq.DEALER:
                for _ in range(self._num_endpoints):
                    self._socket.send_multipart([b'', msg])

                # Account for empty delimiter frame.
                recv_slice = slice(1, None)
            else:
                # There can only be a single endpoint with REP.
                self._socket.send(msg)

            self._recv_ready = True

        try:
            # TODO: No guarantee to be actually matched if the bridges
            # are out of sync themselves.
            replies = [self._socket.recv_multipart(copy=False)[recv_slice]
                       for _ in range(self._num_endpoints)]

        except zmq.error.Again:
            raise TimeoutError(
                'No data received from {} in the last {} ms'.format(
                    self._socket.getsockopt_string(zmq.LAST_ENDPOINT),
                    self._socket.getsockopt(zmq.RCVTIMEO)))
        self._recv_ready = False

        data = {}
        meta = {}

        for reply in replies:
            data_, meta_ = deserialize(reply)
            data.update(data_)
            meta.update(meta_)

        return data, meta

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._context.destroy(linger=0)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()
