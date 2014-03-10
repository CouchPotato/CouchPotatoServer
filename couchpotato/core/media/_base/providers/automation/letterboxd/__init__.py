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
            'description': 'Import movies from any public <a href="http://letterboxd.com/">Letterboxd</a> watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                },
                {
                    'name': 'automation_urls',
                    'label': 'Username',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                },
            ],
        },
    ],
}]
