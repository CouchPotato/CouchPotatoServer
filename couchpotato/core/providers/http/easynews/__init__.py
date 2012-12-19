from .main import Easynews


def start():
    return Easynews()

config = [{
    'name': 'easynews',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'http_providers',
            'name': 'easynews',
            'label': 'Easynews',
            'description': 'Easynews global search',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'label': 'Username',
                },
                {
                    'name': 'password',
                    'label': 'Password',
                },
            ],
        },
    ],
}]
