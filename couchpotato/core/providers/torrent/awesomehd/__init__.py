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
                    'label': 'Only AHD internals',
                    'default': 1,
                    'description': 'Only search for internal releases.'
                },
                {
                    'name': 'prefer_internal',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer AHD internals',
                    'default': 1,
                    'description': 'Favors AHD internal releases over non-internal releases.'
                },
                {
                    'name': 'prefer_encodes',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer x264 Encodes',
                    'default': 1,
                    'description': 'Favors encodes over remuxes.'
                },
                {
                    'name': 'prefer_remuxes',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer Remuxes',
                    'default': 0,
                    'description': 'Favors remuxes over encodes.'
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                },
            ],
        },
    ],
}]

