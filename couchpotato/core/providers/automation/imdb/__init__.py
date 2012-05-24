from .main import IMDB

def start():
    return IMDB()

config = [{
    'name': 'imdb',
    'groups': [
        {
            'tab': 'automation',
            'name': 'imdb_automation',
            'label': 'IMDB',
            'description': 'From any <strong>public</strong> IMDB watchlists. Url should end with <strong>export?list_id=XXXXX&author_id=XXXXX<strong>',
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
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                },
            ],
        },
    ],
}]
