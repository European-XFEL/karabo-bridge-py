Messaging protocol
==================

The Karabo bridge protocol is based on `ZeroMQ <http://zeromq.org/>`_ and
`msgpack <https://msgpack.org/>`_.

The connection can use one of two kinds of ZeroMQ sockets. The client and the
server must be configured to use matching socket types.

* REQ-REP: The client sends the raw ASCII bytes ``next`` (not using msgpack)
  as a request, and the reply is a message as described below. This is the
  default option.
* PUB-SUB: The client subscribes to messages published by the server.
  This is simpler, but can create a lot of network traffic.

.. note::

   The data messages are documented here in terms of *msgpack*.
   The code can also use Python's *pickle* serialisation format,
   but since this is Python specific, it is not recommended for new code.


Message format 1.0
------------------

In the original message format (version ``1.0``), data is sent in a single
ZMQ message part containing a nested dictionary (a msgpack map).

The first level of keys are source names, which typically correspond to Karabo
device names. Each source has a data dictionary representing a flattened Karabo
hash, with dots delimiting successive key levels.
Arrays are serialised using `msgpack_numpy <https://github.com/lebedov/msgpack-numpy>`_.

Each source data dictionary also has a key ``metadata``,
which contains a further nested dictionary with keys:
``source``, ``timestamp``, ``timestamp.tid``, ``timestamp.sec`` and ``timestamp.frac``.

Each source dictionary also has a key ``ignored_keys``, with a list of
strings identifying keys which were filtered out of the data by configuration
options on the bridge server.

.. code-block:: python

    {
        'SPB_DET_AGIPD1M-1/DET/detector': {
            'image.data': array(...),
            # ... other keys
            'metadata': {
                'source': 'SPB_DET_AGIPD1M-1/DET/detector',
                'timestamp': 1526464869.4109755,
                'timestamp.frac': '4109755',
                'timestamp.sec': '1526464869',
                'timestamp.tid': 10000000001
            },
            'ignored_keys': []
        }
    }

Message format 2.0
------------------

This format is currently referred to as ``latest`` in code and configuration
options.

The data is split up into a series of pieces,
allowing arrays to be serialised more efficiently.
Each piece has two ZeroMQ message parts: a msgpack-serialised header,
followed by a data part.
A full message is therefore a multipart ZeroMQ message with an even number
of message parts.

Each header part is a dictionary (a msgpack map) containing at least the keys
``source`` and ``content``. The former is a source name such as
``'SPB_DET_AGIPD1M-1/DET/detector'``. The latter is one of:

* ``'msgpack'``: The following data part is a msgpack map containing the data
  for this source, excluding any array and image data elements. This also
  includes the ``metadata`` and ``ignored_keys`` information as described
  for message format 1.0 above.
* ``'array'``: The following data part is a raw array. The header
  has additional keys describing the array:

  * ``path``: The key of this data, e.g. ``'image.data'``.
  * ``dtype``: A string naming a (numpy) dtype, such as ``'uint16'`` for
    16-bit unsigned integers.
  * ``shape``: An array of integers giving the dimensions of the array.

* ``'ImageData'``: The following data part is a raw array. The header contains
  the same keys as for *array*, plus:

  * ``params``: Image parameters from Karabo (?)

Protocol implementations
------------------------

Clients:

* `Python client <https://github.com/European-XFEL/karabo-bridge-py>`_
* `C++ client <https://github.com/European-XFEL/karabo-bridge-cpp>`_

Servers:

* `PipeToZeroMQ Karabo device <https://in.xfel.eu/gitlab/karaboDevices/PipeToZeroMQ>`_:
  sends data from a live Karabo system.
* `karabo_data Python module <https://karabo-data.readthedocs.io/en/latest/streaming.html>`__:
  can stream data from XFEL HDF5 files.
* The `Python client`_ includes a server to send simulated random data.
