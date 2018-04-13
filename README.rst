===========================
European XFEL Karabo Bridge
===========================

``euxfel_karabo_bridge`` is a Python 3 client to receive pipeline data from the
Karabo control system used at `European XFEL <https://www.xfel.eu/>`_.
A simulated Karabo bridge server is included to allow testing code without
a connection to a real Karabo server.

Installing
----------

to install the package::

    $ python3 -m pip install git+https://github.com/European-XFEL/karabo-bridge-py.git#egg=karabo-bridge-py

    or

    $ git clone https://github.com/European-XFEL/karabo-bridge-py.git
    python3 -m pip install .

How to use
----------

Request data from a karabo bridge server
++++++++++++++++++++++++++++++++++++++++

Use the ``Client`` class from euxfel_karabo_brige to create a client and the
``next`` method to request data from the server.
The returned value is a dictionary containing all data source available in the
pipeline. Each source contains a dictionary containing the (flattened)
key/value pairs for that source's parameters. The values are all built-in python
types, or numpy arrays.

.. code-block:: python

    >>> from euxfel_karabo_bridge import Client
    >>> krb_client = Client('tcp://server-host-name:12345')
    >>> data = krb_client.next()
    >>> data.keys()
    dict_keys(['source1', 'source2', 'source3'])
    >>> data['source1'].keys()
    dict_keys(['param1', 'param2'])

Use the Simulation server
+++++++++++++++++++++++++

To start a simulation, call the ``server_sim`` function and provide a port to bind to.
You can the use the ``Client`` class and connect to it to test the
client without the need to use Karabo.

.. code-block:: python

    >>> from euxfel_karabo_bridge import server_sim
    >>> server_sim(1234)
    Server : buffered train: 15202746822
    Server : buffered train: 15202746823
    Server : buffered train: 15202746824
    Server : buffered train: 15202746825
    Server : buffered train: 15202746826
    Server : buffered train: 15202746827
    ...

