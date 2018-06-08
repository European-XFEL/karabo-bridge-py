#!/usr/bin/env python

import argparse
from time import localtime, strftime, time

from .glimpse import print_train_data
from ..client import Client


def monitor(client, verbosity=0):
    before = time()
    data, metadata = client.next()
    after = time()

    print_train_data(data, metadata, before, after, verbosity=verbosity)

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-monitor",
        description="Monitor data from a Karabo bridge server")
    ap.add_argument('endpoint',
                    help="ZMQ address to connect to, e.g. 'tcp://localhost:4545'")
    ap.add_argument('-v', '--verbose', action='count', default=0,
                    help='Select verbosity (-vvv for most verbose)')
    args = ap.parse_args(argv)

    client = Client(args.endpoint)
    try:
        while True:
            monitor(client, verbosity=args.verbose)
    except KeyboardInterrupt:
        print('\nexit.')
