from .main import Growl

def start():
    return Growl()

config = [{
    'name': 'growl',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'growl',
            'description': 'Version 1.4+',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'on_snatch',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
                {
                    'name': 'hostname',
                    'description': 'Notify growl over network. Needs restart.',
                    'advanced': True,
                },
                {
                    'name': 'port',
                    'type': 'int',
                    'advanced': True,
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'advanced': True,
                },
            ],
        }
    ],
}]
