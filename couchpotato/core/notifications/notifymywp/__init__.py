from .main import NotifyMyWP


def start():
    return NotifyMyWP()

config = [{
    'name': 'notifymywp',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'notifymywp',
            'label': 'Windows Phone',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'description': 'Multiple keys seperated by a comma. Maximum of 5.'
                },
                {
                    'name': 'dev_key',
                    'advanced': True,
                },
                {
                    'name': 'priority',
                    'default': 0,
                    'type': 'dropdown',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)],
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
