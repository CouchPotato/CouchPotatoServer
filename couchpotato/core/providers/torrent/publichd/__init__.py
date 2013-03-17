from .main import PublicHD

def start():
    return PublicHD()

config = [{
    'name': 'publichd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'PublicHD',
            'description': 'Public Torrent site with only HD content. See <a href="https://publichd.se/">PublicHD</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '',
                    'description': 'Adds an extra score for each provided download.',
                }
            ],
        },
    ],
}]
