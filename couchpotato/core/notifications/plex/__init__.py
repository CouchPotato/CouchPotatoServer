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
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                    'description': 'Default should be on localhost',
                    'advanced': True,
                },
            ],
        }
    ],
}]
