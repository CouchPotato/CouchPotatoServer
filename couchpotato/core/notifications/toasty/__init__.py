from .main import Toasty

def start():
    return Toasty()

config = [{
    'name': 'toasty',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'toasty',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Device ID',
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
