#!/usr/bin/env python

from setuptools import setup

setup(name="couchpotato",
      packages=['couchpotato'],
      package_dir={'': 'src'},
      install_requires=[
          'argparse',
          'sqlalchemy',
          'elixir',
          'nose'],
      entry_points="""
      [console_scripts]
      couchpotato = couchpotato.cli:cmd_couchpotato
      """)

