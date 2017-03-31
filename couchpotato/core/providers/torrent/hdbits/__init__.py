from .main import HDBits

def start():
    return HDBits()

config = [{
    'name': 'hdbits',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'HDBits',
            'description': 'See <a href="http://hdbits.org">HDBits</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'passkey',
                    'default': '',
                },
            ],
        },
    ],
}]
