from .main import TorrentLeech

def start():
    return TorrentLeech()

config = [{
    'name': 'torrentleech',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'TorrentLeech',
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
