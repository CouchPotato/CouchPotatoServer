from .main import Letterboxd

def start():
    return Letterboxd()

config = [{
    'name': 'letterboxd',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'letterboxd_automation',
            'label': 'Letterboxd',
            'description': 'import movies from your <a href="http://letterboxd.com/">Letterboxd</a> watchlist',
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