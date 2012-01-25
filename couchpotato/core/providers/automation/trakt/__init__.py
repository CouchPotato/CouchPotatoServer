from .main import Trakt

def start():
    return Trakt()

config = [{
    'name': 'trakt',
    'groups': [
        {
            'tab': 'automation',
            'name': 'trakt_automation',
            'label': 'Trakt',
            'description': 'Enable automatic movie adding from Trakt',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
