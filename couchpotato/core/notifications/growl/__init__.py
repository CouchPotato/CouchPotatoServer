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
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
            ],
        }
    ],
}]
