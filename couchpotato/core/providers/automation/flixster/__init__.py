from .main import Flixster


def start():
    return Flixster()

config = [{
    'name': 'flixster',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'flixster_automation',
            'label': 'Flixster',
            'description': 'Import movies from any public <a href="http://www.flixster.com/">Flixster</a> watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_ids_use',
                    'label': 'Use',
                },
                {
                    'name': 'automation_ids',
                    'label': 'User ID',
                    'type': 'combined',
                    'combine': ['automation_ids_use', 'automation_ids'],
                },
            ],
        },
    ],
}]
