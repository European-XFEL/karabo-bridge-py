Release Notes
=============

0.6.0
-----

- Move server implementation from Extra-data to this package (#58)

0.5.0
-----

- public interface for serializers (#56)
- support dummy timestamps for protocol version 1.0 (#56)
- FIX: prevent altering input data, metadata (#56)
- support zmq PULL socket in `Client` (#57)
- add socket option to cli tools: server-sim, karabo-bridge-glimpse, karabo-bridge-monitor (#57)
- refactor simulation code #57 

0.4.0
-----

- Simulation: option to generate data in file-like stream-like shape (#52)
- Make simulation code able to run on Windows (#54)

0.3.0
-----

- Add timeout option on Client (#46)
- Simulator update to match actual data for AGIPD and LPD detectors at EuXFEL (#47)
- Remove support for pickle serialization (#49)
- remove deprecated 'ImageData' messages (#49)
- add context argument (#49)

0.2.0
-----

- Client receives data more efficiently by asking ZeroMQ to avoid a memory copy for big arrays (#44).
  - The simulator also sends data more efficiently by avoiding another copy.
- Simulator can simulate multiple (similar) sources in each message (#36).
- New simulator option to send data shaped like a single module of AGIPD (#44).
- Simulator code refactored (#42).
- `karabo-bridge-glimpse` now shows the element type for lists and tuples.

