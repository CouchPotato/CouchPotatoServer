from .main import Newzbin

def start():
    return Newzbin()

config = [{
    'name': 'newzbin',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'newzbin',
            'description': 'See <a href="https://www.newzbin2.es/">Newzbin</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
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
            ],
        },
    ],
}]
