Command line tools
==================

.. _cmd-server-sim:

``karabo-bridge-server-sim``
----------------------------

Run a Karabo bridge server producing simulated data in order to test tools
with the karabo bridge client. This sends nonsense data with the same
structure as real data. To start a server, run the command:

.. code-block:: console

   $ karabo-bridge-server-sim 1234
   Simulated Karabo-bridge server started on:
   tcp://hostname:1234

The number (1234) must be an unused local TCP port above 1024.

``karabo-bridge-glimpse``
-------------------------

Get one Karabo bridge message and prints its data structure. optionally: save
its data to an HDF5 file.

.. code-block:: console

   $ karabo-bridge-glimpse tcp://hostname:1234
   Train ID: 10000000000 --------------------------
   Data from 1 sources, REQ-REP took 0.13 ms
   
   Source 1: 'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED' @ 10000000000
   timestamp: 2020-05-06 17:00:31 (1588777231.371173) | delay: 11148.08 ms
   data:
    - [ndarray] image.cellId, uint16, (64,)
    - [ndarray] image.data, float32, (16, 128, 512, 64)
    - [ndarray] image.gain, uint16, (128, 512, 64)
    - [list of str] image.passport, ['SPB_DET_AGIPD1M-1/CAL/THRESHOLDING_Q1M1', ...
    - [ndarray] image.pulseId, uint64, (64,)
    - [ndarray] image.trainId, uint64, (64,)
    - [list of bool] modulesPresent, [True, True, True, True, True, True, True, ...
    - [list of str] sources, ['SPB_DET_AGIPD1M-1/CAL/0CH0:xtdf', 'SPB_DET_AGIPD1...
   metadata:
    - [str] source, SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED
    - [float] timestamp, 1588777231.371173
    - [str] timestamp.frac, 371173000000000000
    - [str] timestamp.sec, 1588777231
    - [int] timestamp.tid, 10000000000

``karabo-bridge-monitor``
-------------------------

Monitor data from a Karabo bridge server.

.. code-block:: console

   $ karabo-bridge-monitor tcp://hostname:1234
   Train ID: 10000000001 --------------------------
   Data from 1 sources, REQ-REP took 0.11 ms
   
   Source 1: 'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED' @ 10000000001
   timestamp: 2020-05-06 17:00:42 (1588777242.3875175) | delay: 50881.01 ms
   - data: ['image.cellId', 'image.data', 'image.gain', 'image.passport', 'image.pulseId', 'image.trainId', 'modulesPresent', 'sources']
   - metadata: ['source', 'timestamp', 'timestamp.frac', 'timestamp.sec', 'timestamp.tid']
   
   Train ID: 10000000002 --------------------------
   Data from 1 sources, REQ-REP took 1.00 ms
   
   Source 1: 'SPB_DET_AGIPD1M-1/CAL/APPEND_CORRECTED' @ 10000000002
   timestamp: 2020-05-06 17:01:33 (1588777293.1563108) | delay: 1127.90 ms
   - data: ['image.cellId', 'image.data', 'image.gain', 'image.passport', 'image.pulseId', 'image.trainId', 'modulesPresent', 'sources']
   - metadata: ['source', 'timestamp', 'timestamp.frac', 'timestamp.sec', 'timestamp.tid']

   ...

