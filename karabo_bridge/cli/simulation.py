import argparse
from karabo_bridge.simulation import start_gen


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-server-sim",
        description="Run a Karabo bridge server producing simulated data.")
    ap.add_argument('port', help="TCP port the server will bind")
    ap.add_argument('--detector', default='AGIPD',
                    choices=['AGIPD', 'LPD'],
                    help="Which kind of detector to simulate (default: AGIPD)")
    ap.add_argument('--protocol', default='2.2',
                    choices=['1.0', '2.1', '2.2'],
                    help="Version of the Karabo Bridge protocol to send (default: 2.2)")
    ap.add_argument('--serialisation', default='msgpack',
                    choices=['msgpack', 'pickle'],
                    help="Message serialisation format (default: msgpack)")
    args = ap.parse_args(argv)
    start_gen(args.port, args.serialisation, args.protocol, args.detector)
