from .main import IPTorrents

def start():
    return IPTorrents()

config = [{
    'name': 'iptorrents',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'IPTorrents',
            'description': 'See <a href="http://www.iptorrents.com">IPTorrents</a>',
            'wizard': True,
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
                    'name': 'freeleech',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Only search for [FreeLeech] torrents.',
                },
            ],
        },
    ],
}]
