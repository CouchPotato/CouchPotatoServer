from .main import XBMC

def start():
    return XBMC()

config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'xbmc',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                    'description': '',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                    'description': '',
                },
                {
                    'name': 'username',
                    'default': 'xbmc',
                    'description': '',
                },
                {
                    'name': 'password',
                    'default': 'xbmc',
                    'type': 'password',
                    'description': '',
                },
            ],
        }
    ],
}]
