from .main import TorrentShack

def start():
    return TorrentShack()

config = [{
    'name': 'torrentshack',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'TorrentShack',
            'description': 'See <a href="http://www.torrentshack.net/">TorrentShack</a>',
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
                    'name': 'scene_only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only allow scene releases.'
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
        },
    ],
}]
