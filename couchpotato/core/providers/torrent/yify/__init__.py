from main import Yify

def start():
    return Yify()

config = [{
    'name': 'yify',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'Yify',
            'description': 'Small HD movies, encoded by Yify.',
            'wizard': False,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True
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
        }
    ]
}]
