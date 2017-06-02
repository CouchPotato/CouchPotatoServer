from .main import Pushover

def start():
    return Pushover()

config = [{
    'name': 'pushover',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'pushover',
            'label': 'Pushover',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'user_key',
                    'description': 'Register on pushover.net to get one.'
                },
                {
                    'name': 'app_token',
                    'description': 'You can get one <a href="https://pushover.net/apps/build">here</a>.'
                },
                {
                    'name': 'priority',
                    'default': 0,
                    'type': 'dropdown',
                    'values': [('Normal', 0), ('High', 1)],
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
