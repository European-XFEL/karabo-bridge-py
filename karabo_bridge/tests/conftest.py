from tempfile import TemporaryDirectory
import pytest

from karabo_bridge.simulation import ServeInThread


@pytest.fixture
def sim_server():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint, detector='AGIPDModule', raw=True):
            yield endpoint


@pytest.fixture
def sim_server_version_1():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint, detector='AGIPDModule', raw=True,
                           protocol_version='1.0'):
            yield endpoint
