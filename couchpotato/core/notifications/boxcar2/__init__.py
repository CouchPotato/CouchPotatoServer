from .main import Boxcar2


def start():
    return Boxcar2()

config = [{
    'name': 'boxcar2',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'boxcar2',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'token',
                    'description': ('Your Boxcar access token.', 'Can be found in the app under settings')
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
