from .main import ILoveTorrents


def start():
    return ILoveTorrents()

config = [{
    'name': 'ilovetorrents',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'ILoveTorrents',
            'description': 'Where the Love of Torrents is Born',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'username',
                    'label': 'Username',
                    'type': 'string',
                    'default': '',
                    'description': 'The user name for your ILT account',
                },
                {
                    'name': 'password',
                    'label': 'Password',
                    'type': 'password',
                    'default': '',
                    'description': 'The password for your ILT account.',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]
