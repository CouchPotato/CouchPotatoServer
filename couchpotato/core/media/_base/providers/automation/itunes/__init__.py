from .main import ITunes


def start():
    return ITunes()

config = [{
    'name': 'itunes',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'itunes_automation',
            'label': 'iTunes',
            'description': 'From any <a href="http://itunes.apple.com/rss">iTunes</a> Store feed. Url should be the RSS link.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                    'default': ',',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                    'default': 'https://itunes.apple.com/rss/topmovies/limit=25/xml,',
                },
            ],
        },
    ],
}]
