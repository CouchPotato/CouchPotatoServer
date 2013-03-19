from .main import NzbIndex

def start():
    return NzbIndex()

config = [{
    'name': 'nzbindex',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'nzb_providers',
            'name': 'nzbindex',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbindex.com/">NZBIndex</a>',
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
                    'default': '',
                    'description': 'Adds an extra score for each provided download.',
                }
            ],
        },
    ],
}]
