#!/usr/bin/env python
import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name="euxfel_karabo_bridge",
      author="The European XFEL",
      author_email="usp-support@xfel.eu",
      description=("Python 3 tools to request data from the Karabo control
                   "system."),
      long_description=read("README.md"),
      url="https://github.com/European-XFEL/karabo-bridge-py",
      license="BSD",
      install_requires=["msgpack-python", "msgpack_numpy", "numpy", "zmq"],
      packages=["euxfel_karabo_bridge"]
      )
