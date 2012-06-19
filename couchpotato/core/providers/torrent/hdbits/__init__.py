from .main import HDBits

def start():
    return HDBits()

config = [{
    'name': 'hdbits',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'HDBits',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
		{
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'passkey',
                    'default': '',
                },
            ],
        },
    ],
}]
