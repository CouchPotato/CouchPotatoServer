from .main import Nzbsrus

def start():
    return Nzbsrus()

config = [{
    'name': 'nzbsrus',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'nzb_providers',
            'name': 'nzbsrus',
            'label': 'Nzbsrus',
            'description': 'See <a href="https://www.nzbsrus.com/">NZBsRus</a>. <strong>You need a VIP account!</strong>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'userid',
                    'label': 'User ID',
                },
                {
                    'name': 'api_key',
                    'default': '',
                    'label': 'Api Key',
                },
                {
                    'name': 'english_only',
                    'default': 1,
                    'type': 'bool',
                    'label': 'English only',
                    'description': 'Only search for English spoken movies on Nzbsrus',
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
