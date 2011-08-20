from .main import Updater

def start():
    return Updater()

config = [{
    'name': 'updater',
    'groups': [
        {
            'tab': 'general',
            'name': 'updater',
            'label': 'Updater',
            'git_only': True,
            'description': 'Enable periodic update checking',
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'type': 'enabler',
                },
                {
                    'name': 'automatic',
                    'default': True,
                    'type': 'bool',
                    'description': 'Automaticly update when update is available',
                },
            ],
        },
    ],
}]
