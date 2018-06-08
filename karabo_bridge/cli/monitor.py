#!/usr/bin/env python

import argparse
from time import localtime, strftime, time

from .glimpse import print_train_data
from ..client import Client


def monitor(client):    
    before = time()
    data, metadata = client.next()
    after = time()
    delta = after - before

    print_train_data(data, metadata, before, after, verbosity=0)

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="karabo-bridge-monitor",
        description="Monitor data from a Karabo bridge server")
    ap.add_argument('endpoint',
                    help="ZMQ address to connect to, e.g. 'tcp://localhost:4545'")
    args = ap.parse_args(argv)

    client = Client(args.endpoint)
    try:
        while True:
            monitor(client)
    except KeyboardInterrupt:
        print('\nexit.')
