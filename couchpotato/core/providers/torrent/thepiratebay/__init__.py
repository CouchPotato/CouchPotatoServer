#!/usr/bin/python
# -*- coding: utf-8 -*-

from main import ThePirateBay
from main import TPBProxy


def start():
    return ThePirateBay()


config = [{'name': 'ThePirateBay', 'groups': [{
    'tab': 'searcher',
    'subtab': 'providers',
    'name': 'ThePirateBay',
    'description': 'The world\'s largest bittorrent tracker.',
    'options': [{'name': 'enabled', 'type': 'enabler',
                'default': False}, {
        'name': 'domain_for_tpb',
        'label': 'Proxy server',
        'default': 'http://thepiratebay.se',
        'description': 'Default domain for requests',
        'type': 'dropdown',
        'values': TPBProxy.list,
        }],
    }]}]
