from .main import Kere

def start():
    return Kere()

config = [{
    'name': 'kere',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'kere',
            'label': 'Kere',
            'description': 'See <a href="http://kere.ws/">Kere</a>',
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
            ],
        },
    ],
}]