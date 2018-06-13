from tempfile import TemporaryDirectory
import pytest

from karabo_bridge.simulation import ServeInThread


@pytest.fixture
def sim_server():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint):
            yield endpoint


@pytest.fixture
def sim_server_pickle():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint, ser='pickle'):
            yield endpoint


@pytest.fixture
def sim_server_version_1():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint, protocol_version='1.0'):
            yield endpoint