from .main import Nzbx

def start():
    return Nzbx()

config = [{
    'name': 'nzbx',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'nzb_providers',
            'name': 'nzbX',
            'description': 'Free provider. See <a href="https://www.nzbx.co/">nzbX</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
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
