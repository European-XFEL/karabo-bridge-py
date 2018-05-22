#!/usr/bin/env python

import argparse
from time import localtime, strftime, time

from ..client import Client


def monitor(client):    
    before = time()
    data = client.next()
    after = time()
    delta = after - before

    sources = list(data.keys())

    print('received {} data sources'.format(len(sources)))
    print('REQ-REP delay (s):', delta)
    for source in sources:
        ts = data[source]['metadata']['timestamp']
        dt = strftime('%Y-%m-%d %H:%M:%S', localtime(ts))
        tid = data[source]['metadata']['timestamp.tid']
        delay = (delta - ts) * 1000
        print('- {}:'.format(source))
        print('delay (ms): {:.2f} | timestamp: {} ({}) | tid: {}'.format(delay, dt, ts, tid))
        # print('  * timestamp: ', ts)
        # print('  * train id:  ', tid)
        # print('  * delay (ms):', delay)
    print()

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
