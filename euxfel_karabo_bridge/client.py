# coding: utf-8
"""
Karabo bridge client.

Copyright (c) 2017, European X-Ray Free-Electron Laser Facility GmbH
All rights reserved.

You should have received a copy of the 3-Clause BSD License along with this
program. If not, see <https://opensource.org/licenses/BSD-3-Clause>
"""

from functools import partial
import msgpack
import numpy as np
import pickle
import re
import zmq


__all__ = ['Client']


class Client:
    """Karabo bridge client for Karabo pipeline data.

    This class can request data to a Karabo bridge server.
    Create the client with::

        from euxfel_karabo_bridge import Client
        krb_client = Client("tcp://153.0.55.21:12345")

    then call ``data = krb_client.next()`` to request next available data
    container.

    Parameters
    ----------
    endpoint : str
        server socket you want to connect to (only support TCP socket).
    sock : str, optional
        socket type - supported: REQ.
    ser : str, optional
        Serialization protocol to use to decode the incoming message (default
        is msgpack) - supported: msgpack,pickle.

    Raises
    ------
    NotImplementedError
        if socker type or serialization algorythm is not supported.
    SyntaxError
        if provided endpoint is not valid.
    """
    def __init__(self, endpoint, sock='REQ', ser='msgpack'):
        if re.match(r'^tcp://.*:\d{1,5}$', endpoint) is None:
            raise SyntaxError("Provided endpoint is invalid:", str(endpoint))

        self._context = zmq.Context()
        self._socket = None
        self._deserializer = None

        if sock == 'REQ':
            self._socket = self._context.socket(zmq.REQ)
            self._socket.setsockopt(zmq.LINGER, 0)
            self._socket.connect(endpoint)
        else:
            raise NotImplementedError('socket is not supported:', str(sock))

        if ser == 'msgpack':
            self._deserializer = partial(msgpack.loads, raw=False)
        elif ser == 'pickle':
            self._deserializer = pickle.loads
        else:
            raise NotImplementedError('serializer is not supported:', str(ser))

    def next(self):
        """Request next data container.

        This function call is blocking.
        """
        self._socket.send(b'next')
        msg = self._socket.recv_multipart()
        return self._deserialize(msg)

    def _deserialize(self, msg):
        if len(msg) < 2:
            return self._deserializer(msg[-1])

        dat = {}
        for header, data in zip(*[iter(msg)]*2):
            md = self._deserializer(header)
            source = md['source']
            content = md['content']

            if content in ('msgpack', 'pickle.HIGHEST_PROTOCOL',
                           'pickle.DEFAULT_PROTOCOL'):
                dat[source] = self._deserializer(data)
            elif content in ('array', 'ImageData'):
                dtype = md['dtype']
                shape = md['shape']

                buf = memoryview(data)
                array = np.frombuffer(buf, dtype=dtype).reshape(shape)

                if content == 'array':
                    dat[source].update({md['path']: array})
                else:
                    dat[source].update({md['path']: md['params']})
                    dat[source][md['path']]['Data'] = array
            else:
                raise RuntimeError('unknown message content:', md['content'])
        return dat
