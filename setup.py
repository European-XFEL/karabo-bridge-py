#!/usr/bin/env python
import os.path as osp
import re
from setuptools import setup
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


setup(name="euxfel_karabo_bridge",
      version=find_version("euxfel_karabo_bridge", "__init__.py"),
      author="European XFEL GmbH",
      author_email="cas-support@xfel.eu",
      maintainer="Thomas Michelat",
      url="https://github.com/European-XFEL/karabo-bridge-py",
      description=("Python 3 tools to request data from the Karabo control"
                   "system."),
      long_description=read("README.rst"),
      license="BSD-3-Clause",
      install_requires=[r for r in read('requirements.txt').splitlines()],
      packages=["euxfel_karabo_bridge"],
    #   scripts=["bin/glimpse"],
      entry_points={
          'console_scripts': [
              'krbb_glimpse=euxfel_karabo_bridge.cli.glimpse:main',
#              'krbb_server_sim=euxfel_karabo_bridge.simulation:server_sim'
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
      ]
      )
