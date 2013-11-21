from .main import Couchtarter

def start():
    return Couchtarter()

config = [{
    'name': 'couchtart',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'couchtart',
            'order': 10,
            'description': 'Cocuhtart providers.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
                {
                    'name': 'use',
                    'default': '0,0,0,0,0,0'
                },
                {
                    'name': 'host',
                    'default': '',
                    'description': 'The url path of your Couchtart provider.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '0',
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'pass_key',
                    'default': ',',
                    'label': 'Pass Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'username', 'pass_key', 'extra_score'],
                },
            ],
        },
    ],
}]
