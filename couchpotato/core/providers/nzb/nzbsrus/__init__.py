from .main import Nzbsrus

def start():
    return Nzbsrus()

config = [{
    'name': 'nzbsrus',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'nzbsrus',
            'label': 'Nzbsrus',
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
            ],
        },
    ],
}]
