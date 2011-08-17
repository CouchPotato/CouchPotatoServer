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
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'type': 'enabler',
                    'description': 'Enable periodic update checking',
                },
                {
                    'name': 'automatic',
                    'default': False,
                    'type': 'enabler',
                    'description': 'Automaticly update when update is available',
                },
            ],
        },
    ],
}]
