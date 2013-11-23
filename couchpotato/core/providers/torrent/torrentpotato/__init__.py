from .main import Couchtater

def start():
    return Couchtater()

config = [{
    'name': 'couchtater',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'couchtart',
            'order': 10,
            'description': 'Couchtater providers.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'use',
                    'default': ''
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
                    'name': 'name',
                    'default': '',
                },
                {
                    'name': 'pass_key',
                    'default': ',',
                    'label': 'Pass Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'name', 'pass_key', 'extra_score'],
                },
            ],
        },
    ],
}]
