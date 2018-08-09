#!/usr/bin/env bash
# Start simulated experiment, which offers data as the KaraboBridge
# would be during the experiment:
echo "demo.sh: starting (simulated) server"
karabo-bridge-server-sim 4545 &
SIMULATION_PID=$!

# Start client to read 10 trains
echo "demo.sh: starting client"
python3 demo.py


# shutting down simulated experiment
echo "demo.sh: killing simulated Karabo Bridge"
kill $SIMULATION_PID
