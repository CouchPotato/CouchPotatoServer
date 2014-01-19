from .main import Plex


def start():
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
