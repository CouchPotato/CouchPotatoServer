from .main import ITunes 

def start():
    return ITunes()

config = [{
    'name': 'itunes',
    'groups': [
        {
            'tab': 'automation',
            'name': 'itunes_automation',
            'label': 'iTunes',
            'description': 'From any <a href="http://itunes.apple.com/rss">iTunes</a> Store feed. Url should be the RSS link. (uses minimal requirements)',
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
