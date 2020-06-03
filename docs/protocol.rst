.. _karabo_bridge_protocol:

Data container
==============

The data object returned by :meth:`Client.next` is a tuple of two nested
dictionaries, holding data and metadata respectively.

The first level of keys in both dictionaries are source names,
which typically correspond to Karabo device names.

In the data dictionary, each source has a dictionary representing a flattened
Karabo hash, with dots delimiting successive key levels.
The values are either basic Python types such as strings and floats,
or numpy arrays.

In the metadata dictionary, each source has a dictionary with keys: ``source``,
``timestamp``, ``timestamp.tid``, ``timestamp.sec``, ``timestamp.frac``
and ``ignored_keys``, which is a list of strings identifying keys which were
filtered out of the data by configuration options on the bridge server.

.. code-block:: python

    (
        {   # Metadata
            'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf': {
                'source': 'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf',
                'timestamp': 1526464869.4109755,
                # Timestamps can have attosecond resolution: 18 fractional digits
                'timestamp.frac': '410975500000000000',
                'timestamp.sec': '1526464869',
                'timestamp.tid': 10000000001,
                'ignored_keys': []
            },
        },
        {   # Data
            'SPB_DET_AGIPD1M-1/DET/0CH0:xtdf': {
                'image.data': array(...),
                'header.pulseCount': 64,
                # ... other keys
            }
        }
    )


Karabo Bridge protocol
======================

The Karabo bridge protocol is based on `ZeroMQ <http://zeromq.org/>`_ and
`msgpack <https://msgpack.org/>`_.

The connection can use one of two kinds of ZeroMQ sockets. The client and the
server must be configured to use matching socket types.

* REQ-REP: The client sends the raw ASCII bytes ``next`` (not using msgpack)
  as a request, and the reply is a message as described below. This is the
  default option.
* PUB-SUB: The client subscribes to messages published by the server.
  This is simpler, but can create a lot of network traffic.

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
``source``, ``timestamp``, ``timestamp.tid``, ``timestamp.sec``, ``timestamp.frac``,
and ``ignored_keys``, which is a list of strings identifying keys which were
filtered out of the data by configuration options on the bridge server.

.. code-block:: python

    {
        'SPB_DET_AGIPD1M-1/DET/detector': {
            'image.data': array(...),
            # ... other keys
            'metadata': {
                'source': 'SPB_DET_AGIPD1M-1/DET/detector',
                'timestamp': 1526464869.4109755,
                'timestamp.frac': '410975500000000000',
                'timestamp.sec': '1526464869',
                'timestamp.tid': 10000000001,
                'ignored_keys': []
            },
        }
    }

Message format 2.2
------------------

We have skipped describing message formats 2.0 and 2.1, as we don't know of any
code that used them before version 2.2 was defined.

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
  for this source, excluding any arrays.
  The header map also includes the ``metadata`` information
  as described for message format 1.0 above.
* ``'array'``: The following data part is a raw array. The header
  has additional keys describing the array:

  * ``path``: The key of this data, e.g. ``'image.data'``.
  * ``dtype``: A string naming a (numpy) dtype, such as ``'uint16'`` for
    16-bit unsigned integers.
  * ``shape``: An array of integers giving the dimensions of the array.

A multipart message might contain data from several sources.
For each source, there is one header-data pair with ``'msgpack'`` content,
followed by zero or more header-data pairs for arrays.

.. versionchanged:: 2.2

  Moved metadata from the data to the header.

Image data
----------

Karabo ``ImageData`` objects, holding images from cameras, are represented by a
number of keys with a common prefix. This keys following this prefix include:

- ``.data``: numpy array
- ``.bitsPerPixels`` int
- ``.dimensions`` list of int
- ``.dimensionScales`` str
- ``.dimensionTypes`` list of int
- ``.encoding`` str
- ``.geometry.alignment.offsets`` list of float
- ``.geometry.alignment.rotations`` list of float
- ``.geometry.pixelRegion`` list of int
- ``.geometry.subAssemblies`` list of dict
- ``.geometry.tileId`` int
- ``.header`` user defined dict
- ``.ROIOffsets``  list of int
- ``.binning`` list of int

Minor changes to this list may occur without a new protocol version.

Protocol implementations
------------------------

Clients:

* `Python client <https://github.com/European-XFEL/karabo-bridge-py>`_
* `C++ client <https://github.com/European-XFEL/karabo-bridge-cpp>`_

Servers:

* `PipeToZeroMQ Karabo device <https://in.xfel.eu/gitlab/karaboDevices/PipeToZeroMQ>`_:
  sends data from a live Karabo system.
* The `Python client`_ includes a :ref:`server <cmd-server-sim>` to send simulated random data.
