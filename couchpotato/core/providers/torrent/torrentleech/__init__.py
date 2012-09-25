from .main import TorrentLeech

def start():
    return TorrentLeech()

config = [{
    'name': 'torrentleech',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'torrent_providers',
            'name': 'TorrentLeech',
            'description': 'See <a href="http://torrentleech.org">TorrentLeech</a>',
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
            ],
        },
    ],
}]
