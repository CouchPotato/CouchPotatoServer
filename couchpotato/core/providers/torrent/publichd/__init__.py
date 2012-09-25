from .main import PublicHD

def start():
    return PublicHD()

config = [{
    'name': 'publichd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'torrent_providers',
            'name': 'PublicHD',
            'description': 'Public Torrent site with only HD content. See <a href="http://publichd.eu/">PublicHD</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
            ],
        },
    ],
}]
