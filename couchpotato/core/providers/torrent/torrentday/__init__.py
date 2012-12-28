from .main import TorrentDay

def start():
    return TorrentDay()

config = [{
    'name': 'torrentday',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'torrent_providers',
            'name': 'TorrentDay',
            'description': 'See <a href="http://www.td.af/">TorrentDay</a>',
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
