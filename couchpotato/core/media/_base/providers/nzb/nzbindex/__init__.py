from .main import NzbIndex


def start():
    return NzbIndex()

config = [{
    'name': 'nzbindex',
    'groups': [
        {
            'tab': 'searcher',
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
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
