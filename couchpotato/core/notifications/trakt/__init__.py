from .main import Trakt

def start():
    return Trakt()

config = [{
    'name': 'Trakt',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'trakt',
            'label': 'Trakt',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
            ],
        }
    ],
}]
