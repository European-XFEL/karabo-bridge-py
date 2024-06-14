Karabo Bridge
=============

**Karabo bridge** is a proxy interface to stream data to tools that are not
integrated into the Karabo framework.
It can be configured to provide any detector or control data.
This interface is primarily for online data analysis (near real-time),
but the this package can also stream data from files using the same protocol.

We provide additionally a `c++ client
<https://github.com/European-XFEL/karabo-bridge-cpp>`__, but you can also write
your own code to receive the data if necessary.


.. toctree::
   :caption: Installation

   installation

.. toctree::
   :caption: Description and Tools
   :maxdepth: 2

   protocol
   cli
   euxfel

.. toctree::
   :caption: Reference
   :maxdepth: 2

   reference

.. toctree::
   :caption: Development
   :maxdepth: 2

   changelog


