from .main import Prowl


def start():
    return Prowl()

config = [{
    'name': 'prowl',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'prowl',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Api key',
                },
                {
                    'name': 'priority',
                    'default': '0',
                    'type': 'dropdown',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)]
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
