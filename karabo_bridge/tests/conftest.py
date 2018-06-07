from tempfile import TemporaryDirectory
import pytest

from karabo_bridge.simulation import ServeInThread

@pytest.fixture
def sim_server():
    with TemporaryDirectory() as td:
        endpoint = "ipc://{}/server".format(td)
        with ServeInThread(endpoint):
            yield endpoint
