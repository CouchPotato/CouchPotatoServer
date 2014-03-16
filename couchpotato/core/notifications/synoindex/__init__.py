from .main import Synoindex


def start():
    return Synoindex()

config = [{
    'name': 'synoindex',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'synoindex',
            'description': 'Automaticly adds index to Synology Media Server.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                }
            ],
        }
    ],
}]
