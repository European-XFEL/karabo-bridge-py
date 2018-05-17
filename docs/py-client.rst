Python client interface
=======================

The ``karabo_bridge`` Python package provides a client interface to receive data
from the Karabo bridge.

.. module:: karabo_bridge


.. autoclass:: Client

   .. automethod:: next

Data container
--------------

The data object returned by :meth:`Client.next` is a nested dictionary.

The first level of keys are source names, which typically correspond to Karabo
device names. Each source has a data dictionary representing a flattened Karabo
hash, with dots delimiting successive key levels. The values are either basic
Python types such as strings and floats, or numpy arrays.

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
                # Timestamps can have attosecond resolution: 18 fractional digits
                'timestamp.frac': '410975500000000000',
                'timestamp.sec': '1526464869',
                'timestamp.tid': 10000000001
            },
            'ignored_keys': []
        }
    }

.. note::

   Image data from cameras may have further levels of nested dictionaries.
   This will probably be changed before it's important to properly document it.
