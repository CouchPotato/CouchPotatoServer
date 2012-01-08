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
                    'name': 'notification',
                    'type': 'bool',
                    'default': True,
                    'description': 'Send a notification if an update is available.',
                },
                {
                    'name': 'automatic',
                    'default': True,
                    'type': 'bool',
                    'description': 'Automaticly update when update is available',
                },
                {
                    'name': 'git_command',
                    'default': 'git',
                    'advanced': True
                },
            ],
        },
    ],
}]
