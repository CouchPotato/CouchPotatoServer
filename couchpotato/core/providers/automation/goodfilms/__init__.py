from .main import Goodfilms


def start():
    return Goodfilms()

config = [{
    'name': 'goodfilms',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'goodfilms_automation',
            'label': 'Goodfilms',
            'description': 'import movies from your <a href="http://goodfil.ms">Goodfilms</a> queue',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_username',
                    'label': 'Username',
                },
            ],
        },
    ],
}]
