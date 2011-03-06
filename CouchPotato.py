#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Wrapper for the command line interface.'''

from os.path import dirname
import os
import sys

# Root path
base_path = dirname(os.path.abspath(__file__))

# Insert local directories into path
sys.path.insert(0, os.path.join(base_path, 'libs'))

from couchpotato.core.logger import CPLog
log = CPLog(__name__)


from couchpotato import cli
if __name__ == '__main__':
    try:
        cli.cmd_couchpotato(base_path, sys.argv[1:])
    except Exception, e:
        log.critical(e)
