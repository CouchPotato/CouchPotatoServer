from .main import PublicHD

def start():
    return PublicHD()

config = [{
    'name': 'publichd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'PublicHD',
            'description': 'Public Torrent site with only HD content.',
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