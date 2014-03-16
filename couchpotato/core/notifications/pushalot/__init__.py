from .main import Pushalot


def start():
    return Pushalot()

config = [{
    'name': 'pushalot',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'pushalot',
            'description': 'for Windows Phone and Windows 8',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'auth_token',
                    'label': 'Auth Token',
                },
                {
                    'name': 'silent',
                    'label': 'Silent',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Don\'t send Toast notifications. Only update Live Tile',
                },
                {
                    'name': 'important',
                    'label': 'High Priority',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Send message with High priority.',
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
