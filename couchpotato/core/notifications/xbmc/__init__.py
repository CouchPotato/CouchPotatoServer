from .main import XBMC

def start():
    return XBMC()

config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'xbmc',
            'label': 'XBMC',
            'description': 'v12 (Frodo)',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                },
                {
                    'name': 'username',
                    'default': 'xbmc',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
            ],
        }
    ],
}]
