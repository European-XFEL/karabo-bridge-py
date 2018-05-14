#!/usr/bin/env python

import sys
from time import localtime, strftime, time

from .utils import entrypoint
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
