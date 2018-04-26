import sys

from .glimpse import dict_to_hdf5
from .monitor import monitor as _monitor
from .utils import entrypoint
from ..client import Client
from ..simulation import server_sim


@entrypoint
def glimpse():
    """Karabo bridge glimpse.

    Request 1 train data from a karabo bridge server and dump it to a file.
    
        krbb_glimpse [host] [port]
      
    e.g.    
        $ krbb_glimpse 10.254.0.64 4500
        $ ls
        10.254.0.64_4500_20180301_1205134.h5
    """
    assert len(sys.argv) > 2
    _, host, port, = sys.argv
    assert port.isdigit()

    endpoint = 'tcp://{}:{}'.format(host, port)
    print('get train data from', endpoint)

    client = Client(endpoint)
    data = client.next()

    dict_to_hdf5(data, endpoint)


@entrypoint
def monitor():
    """Debug tools for karabo bridge server.

    Provides useful information on the data comming from a karabo brige server.

    e.g.
        $ krbb_monitor 10.254.0.64 4500
    """
    assert len(sys.argv) > 2
    _, host, port, = sys.argv
    assert port.isdigit()

    endpoint = 'tcp://{}:{}'.format(host, port)
    print('connecting to', endpoint)

    client = Client(endpoint)

    try:
        while True:
            _monitor(client)            
    except KeyboardInterrupt:
        print('\nexit.')


@entrypoint
def simulation():
    """Karabo Bridge server simulation example.

    Send simulated data for detectors present at XFEL.eu

      krbb_server_sim PORT [SER] [DET]

    PORT
        the port on which the server is bound.

    SER
        the serialization function. [pickle, msgpack]

    DET
        the detector to simulate [AGIPD, LPD]

    e.g.
      $ krbb_server_sim 4545
    """
    if len(sys.argv) < 2:
        print("Need to provide at least the port as an argument.\n")
        print("For example: ")
        print("$ python {} 4545".format(sys.argv[0]))
        sys.exit(1)

    _, port, *options = sys.argv
    server_sim(port, options)