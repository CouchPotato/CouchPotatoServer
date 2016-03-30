from .main import Plex


def autoload():
    return Plex()

config = [{
    'name': 'plex',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'plex',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'media_server',
                    'label': 'Media Server',
                    'default': 'localhost',
                    'description': 'Hostname/IP, default localhost'
                },
                {
                    'name': 'username',
                    'label': 'Username',
                    'default': '',
                    'description': 'Required for myPlex'
                },
                {
                    'name': 'password',
                    'label': 'Password',
                    'default': '',
                    'type': 'password',
                    'description': 'Required for myPlex'
                },
                {
                    'name': 'auth_token',
                    'label': 'Auth Token',
                    'default': '',
                    'advanced': True,
                    'description': 'Required for myPlex'
                },
                {
                    'name': 'clients',
                    'default': '',
                    'description': 'Comma separated list of client names\'s (computer names). Top right when you start Plex'
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
