Release Notes
=============

0.6.0
-----

- Move server implementation from Extra-data to this package (:ghpull:`58`)

0.5.0
-----

- public interface for serializers (:ghpull:`56`)
- support dummy timestamps for protocol version 1.0 (:ghpull:`56`)
- FIX: prevent altering input data, metadata (:ghpull:`56`)
- support zmq PULL socket in `Client` (:ghpull:`57`)
- add socket option to cli tools: server-sim, karabo-bridge-glimpse, karabo-bridge-monitor (:ghpull:`57`)
- refactor simulation code (:ghpull:`57`) 

0.4.0
-----

- Simulation: option to generate data in file-like stream-like shape (:ghpull:`52`)
- Make simulation code able to run on Windows (:ghpull:`54`)

0.3.0
-----

- Add timeout option on Client (:ghpull:`46`)
- Simulator update to match actual data for AGIPD and LPD detectors at EuXFEL (:ghpull:`47`)
- Remove support for pickle serialization (:ghpull:`49`)
- remove deprecated 'ImageData' messages (:ghpull:`49`)
- add context argument (:ghpull:`49`)

0.2.0
-----

- Client receives data more efficiently by asking ZeroMQ to avoid a memory copy for big arrays (:ghpull:`44`).
  - The simulator also sends data more efficiently by avoiding another copy.
- Simulator can simulate multiple (similar) sources in each message (:ghpull:`36`).
- New simulator option to send data shaped like a single module of AGIPD (:ghpull:`44`).
- Simulator code refactored (:ghpull:`42`).
- `karabo-bridge-glimpse` now shows the element type for lists and tuples.

