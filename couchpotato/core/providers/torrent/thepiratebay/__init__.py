#!/usr/bin/python
# -*- coding: utf-8 -*-

from main import ThePirateBay


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
        'description': 'Which domain do you preferr(or it\'s not blocked)',
        'type': 'dropdown',
        'values': [
            ('(Sweden) thepiratebay.se', 'http://thepiratebay.se'),
            ('(Sweden) tpb.ipredator.se (ssl)',
             'https://tpb.ipredator.se'),
            ('(Germany) depiraatbaai.be', 'http://depiraatbaai.be'),
            ('(UK) piratereverse.info (ssl)',
             'https://piratereverse.info'),
            ('(UK) tpb.pirateparty.org.uk (ssl)',
             'https://tpb.pirateparty.org.uk'),
            ('(Netherlands) thepiratebay.se.coevoet.nl',
             'http://thepiratebay.se.coevoet.nl'),
            ('(direct) 194.71.107.80', 'http://194.71.107.80'),
            ('(direct) 194.71.107.83', 'http://194.71.107.81'),
            ],
        }],
    }]}]
