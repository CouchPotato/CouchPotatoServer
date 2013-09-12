from main import NextGenRSS

def start():
    return NextGenRSS()

config = [{
    'name': 'nextgenrss',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'NextGen(RSS)',
            'description': 'See <a href="http://nxtgn.org">NextGen</a>',
			'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'rssurl',
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
                    'default': 48,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 10,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
