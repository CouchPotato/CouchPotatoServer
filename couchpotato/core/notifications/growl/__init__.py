from .main import Growl

def start():
    return Growl()

config = [{
    'name': 'growl',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'growl',
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
