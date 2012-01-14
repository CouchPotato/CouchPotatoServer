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
                    'name': 'on_snatch',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
