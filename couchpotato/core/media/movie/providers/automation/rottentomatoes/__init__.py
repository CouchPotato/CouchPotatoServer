from .main import Rottentomatoes


def start():
    return Rottentomatoes()

config = [{
    'name': 'rottentomatoes',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'rottentomatoes_automation',
            'label': 'Rottentomatoes',
            'description': 'Imports movies from rottentomatoes rss feeds specified below.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                    'default': '1',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                    'default': 'http://www.rottentomatoes.com/syndication/rss/in_theaters.xml',
                },
                {
                    'name': 'tomatometer_percent',
                    'default': '80',
                    'label': 'Tomatometer',
                    'description': 'Use as extra scoring requirement',
                },
            ],
        },
    ],
}]
