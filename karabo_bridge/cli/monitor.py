#!/usr/bin/env python
"""Monitor messages coming from Karabo bridge."""

import argparse
import gc

from .glimpse import print_one_train
from ..client import Client


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-monitor",
        description="Monitor data from a Karabo bridge server")
    ap.add_argument('endpoint',
                    help="ZMQ address to connect to, e.g. 'tcp://localhost:4545'")
    ap.add_argument('-z', '--server-socket', default='REP', choices=['REP', 'PUB', 'PUSH'],
                    help='Socket type used by the karabo bridge server (default REP)')
    ap.add_argument('-v', '--verbose', action='count', default=0,
                    help='Select verbosity (-vvv for most verbose)')
    ap.add_argument('--ntrains', help="Stop after N trains", metavar='N',
                    type=int)
    args = ap.parse_args(argv)

    socket_map = {'REP': 'REQ', 'PUB': 'SUB', 'PUSH': 'PULL'}
    client = Client(args.endpoint, sock=socket_map[args.server_socket])
    try:
        if args.ntrains is None:
            while True:
                print_one_train(client, verbosity=args.verbose)
                # Explicitly trigger garbage collection,
                # seems to be needed to avoid using lots of memory.
                gc.collect()
        else:
            for _ in range(args.ntrains):
                print_one_train(client, verbosity=args.verbose)
                # Explicitly trigger garbage collection,
                # seems to be needed to avoid using lots of memory.
                gc.collect()
    except KeyboardInterrupt:
        print('\nexit.')
