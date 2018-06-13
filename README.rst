===========================
European XFEL Karabo Bridge
===========================

.. image:: https://travis-ci.org/European-XFEL/karabo-bridge-py.svg?branch=master
  :target: https://travis-ci.org/European-XFEL/karabo-bridge-py

.. image:: https://codecov.io/gh/European-XFEL/karabo-bridge-py/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/European-XFEL/karabo-bridge-py



``karabo_bridge`` is a Python 3 client to receive pipeline data from the
Karabo control system used at `European XFEL <https://www.xfel.eu/>`_.
A simulated Karabo bridge server is included to allow testing code without
a connection to a real Karabo server.

Installing
----------

to install the package::

    $ python3 -m pip install karabo-bridge

    or

    $ git clone https://github.com/European-XFEL/karabo-bridge-py.git
    $ cd ./karabo-bridge-py
    $ python3 -m pip install .

How to use
----------

Request data from a karabo bridge server
++++++++++++++++++++++++++++++++++++++++

Use the ``Client`` class from karabo_brige to create a client and the
``next`` method to request data from the server.
The function returns 2 dictionaries: the first one holds a train data and the
second one holds the associated train metadata. Both dictionaries are keyed by
source name, and the values are dictionaries containing parameters name and
values for data and metadata information (source name, timestamp, trainId)
for the metadata. Values are all built-in python types, or numpy arrays.

.. code-block:: python

    >>> from karabo_bridge import Client
    >>> krb_client = Client('tcp://server-host-name:12345')
    >>> data, metadata = krb_client.next()
    >>> data.keys()
    dict_keys(['source1', 'source2', 'source3'])
    >>> data['source1'].keys()
    dict_keys(['param1', 'param2'])
    >>> metadata['source1']
    {'source1': {'source': 'source1',
      'timestamp': 1528476983.744877,
      'timestamp.frac': '744877000000000000',
      'timestamp.sec': '1528476983',
      'timestamp.tid': 10000000073}}

Use the Simulation server
+++++++++++++++++++++++++

To start a simulation, call the ``start_gen`` function and provide a port to
bind to. You can the use the ``Client`` class and connect to it to test the
client without the need to use Karabo.

.. code-block:: python

    >>> from karabo_bridge import start_gen
    >>> start_gen(1234)
    Server : emitted train: 10000000000
    Server : emitted train: 10000000001
    Server : emitted train: 10000000002
    Server : emitted train: 10000000003
    Server : emitted train: 10000000004
    ...


You can also run the simulated server from the command line::

    $ karabo-bridge-server-sim 1234
