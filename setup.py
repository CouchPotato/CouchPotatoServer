#!/usr/bin/env python
"""You need to have setuptools installed.

Usage:
    python setup.py develop

This will register the couchpotato package in your system and thereby make it
available from anywhere.

Also, a script will be installed to control couchpotato from the shell.
Try running:
    couchpotato --help

"""

from setuptools import setup

setup(name="couchpotato",
      packages=['couchpotato'],
      package_dir={'': 'src'},
      install_requires=[
          'argparse',
          'elixir',
          'flask',
          'nose',
          'sqlalchemy'],
      entry_points="""
      [console_scripts]
      couchpotato = couchpotato.cli:cmd_couchpotato
      """)

