from .main import NZBMatrix

def start():
    return NZBMatrix()

config = [{
    'name': 'nzbmatrix',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'nzbmatrix',
            'label': 'NZBMatrix',
            'description': 'See <a href="https://nzbmatrix.com/">NZBMatrix</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
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
                    'description': 'Only search for English spoken movies on NZBMatrix',
                },
            ],
        },
    ],
}]
