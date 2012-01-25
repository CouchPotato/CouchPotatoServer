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
            'description': 'from watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_api_key',
                    'label': 'Apikey',
                },
                {
                    'name': 'automation_username',
                    'label': 'Username',
                },
            ],
        },
    ],
}]
