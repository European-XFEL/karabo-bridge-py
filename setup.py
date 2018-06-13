#!/usr/bin/env python
import os.path as osp
import re
from setuptools import setup, find_packages
import sys


def get_script_path():
    return osp.dirname(osp.realpath(sys.argv[0]))


def read(*parts):
    return open(osp.join(get_script_path(), *parts)).read()


def find_version(*parts):
    vers_file = read(*parts)
    match = re.search(r'^__version__ = "(\d+\.\d+\.\d+)"', vers_file, re.M)
    if match is not None:
        return match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(name="karabo_bridge",
      version=find_version("karabo_bridge", "__init__.py"),
      author="European XFEL GmbH",
      author_email="cas-support@xfel.eu",
      maintainer="Thomas Michelat",
      url="https://github.com/European-XFEL/karabo-bridge-py",
      description=("Python 3 tools to request data from the Karabo control"
                   "system."),
      long_description=read("README.rst"),
      license="BSD-3-Clause",
      install_requires=[
          'msgpack>=0.5.4',
          'msgpack-numpy',
          'numpy',
          'pyzmq>=17.0.0',
      ],
      extras_require={
          'test': [
              'pytest',
              'pytest-cov',
              'h5py',
              'testpath',
          ]
      },
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'karabo-bridge-glimpse=karabo_bridge.cli.glimpse:main',
              'karabo-bridge-monitor=karabo_bridge.cli.monitor:main',
              'karabo-bridge-server-sim=karabo_bridge.cli.simulation:main',
              ],
      },
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: BSD License',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
      ])
