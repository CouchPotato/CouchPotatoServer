from .main import Pushbullet


def start():
    return Pushbullet()

config = [{
    'name': 'pushbullet',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'pushbullet',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'User API Key'
                },
                {
                    'name': 'devices',
                    'default': '',
                    'advanced': True,
                    'description': 'IDs of devices to send notifications to, empty = all devices'
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
