from .main import AwesomeHD


def start():
    return AwesomeHD()

config = [{
    'name': 'awesomehd',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Awesome-HD',
            'description': 'See <a href="https://awesome-hd.net">AHD</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'passkey',
                    'default': '',
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
                    'name': 'only_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Only search for internal releases.'
                },
                {
                    'name': 'prefer_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Favors internal releases over non-internal releases.'
                },
                {
                    'name': 'favor',
                    'advanced': True,
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('Encodes & Remuxes', 'both'), ('Encodes', 'encode'), ('Remuxes', 'remux'), ('None', 'none')],
                    'description': 'Give extra scoring to encodes or remuxes.'
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                },
            ],
        },
    ],
}]

