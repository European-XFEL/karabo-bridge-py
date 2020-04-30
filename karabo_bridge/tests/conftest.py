from tempfile import TemporaryDirectory

import numpy as np
import pytest

from karabo_bridge.server import ServerInThread, SimServerInThread


@pytest.fixture(params=['1.0', '2.2'])
def protocol_version(request):
    yield request.param


@pytest.fixture(scope='function')
def sim_server(protocol_version):
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with SimServerInThread(endpoint, detector='AGIPDModule', raw=True,
                               protocol_version=protocol_version) as s:
            yield s


@pytest.fixture(scope='function')
def sim_push_server(protocol_version):
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/push".format(td)
        with SimServerInThread(endpoint, sock='PUSH', detector='AGIPDModule',
                               raw=True, protocol_version=protocol_version) as s:
            yield s


@pytest.fixture(scope='function')
def server(protocol_version):
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServerInThread(endpoint, protocol_version=protocol_version) as s:
            yield s


@pytest.fixture(scope='session')
def data():
    yield {
        'source1': {
            'parameter.1.value': 123,
            'parameter.2.value': 1.23,
            'list.of.int': [1, 2, 3],
            'string.param': 'True',
            'boolean': False,
            'metadata': {'timestamp.tid': 9876543210, 'timestamp': 12345678},
        },
        'XMPL/DET/MOD0': {
            'image.data': np.random.randint(255, size=(2, 3, 4), dtype=np.uint8),
            'something.else': ['a', 'bc', 'd'],
        },
    }


@pytest.fixture(scope='session')
def metadata():
    yield {
        'source1': {
            'source': 'source1',
            'timestamp': 1585926035.7098422,
            'timestamp.sec': '1585926035',
            'timestamp.frac': '709842200000000000',
            'timestamp.tid': 1000000
        },
        'XMPL/DET/MOD0': {
            'source': 'XMPL/DET/MOD0',
            'timestamp': 1585926036.9098422,
            'timestamp.sec': '1585926036',
            'timestamp.frac': '909842200000000000',
            'timestamp.tid': 1000010
        }
    }
