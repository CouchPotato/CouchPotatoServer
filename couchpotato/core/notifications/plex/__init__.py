from .main import Plex

def start():
    return Plex()

config = [{
    'name': 'plex',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'plex',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                    'description': '',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                    'description': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                    'description': '',
                },
            ],
        }
    ],
}]
