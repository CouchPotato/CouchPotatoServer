from .main import AwesomeHD

def start():
    return AwesomeHD()

config = [{
    'name': 'awesomehd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
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

