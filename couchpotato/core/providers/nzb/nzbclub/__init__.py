from .main import NZBClub

def start():
    return NZBClub()

config = [{
    'name': 'nzbclub',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'nzb_providers',
            'name': 'NZBClub',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbclub.com/">NZBClub</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '',
                    'description': 'Adds an extra score for each provided download.',
                }
            ],
        },
    ],
}]
