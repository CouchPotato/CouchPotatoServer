from .main import TorrentPotato


def start():
    return TorrentPotato()

config = [{
    'name': 'torrentpotato',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentPotato',
            'order': 10,
            'description': 'CouchPotato torrent provider. Checkout <a href="https://github.com/RuudBurger/CouchPotatoServer/wiki/CouchPotato-Torrent-Provider">the wiki page about this provider</a> for more info.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'use',
                    'default': ''
                },
                {
                    'name': 'host',
                    'default': '',
                    'description': 'The url path of your TorrentPotato provider.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '0',
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'name',
                    'label': 'Username',
                    'default': '',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'default': '1',
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'default': '40',
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'pass_key',
                    'default': ',',
                    'label': 'Pass Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'pass_key', 'name', 'seed_ratio', 'seed_time', 'extra_score'],
                },
            ],
        },
    ],
}]
