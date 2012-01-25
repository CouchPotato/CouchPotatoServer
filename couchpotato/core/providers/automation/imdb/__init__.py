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
            'description': 'Enable automatic movie adding of IMDB watchlists',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls',
                },
            ],
        },
    ],
}]
