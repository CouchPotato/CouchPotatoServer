from .main import FTDWorld

def start():
    return FTDWorld()

config = [{
    'name': 'ftdworld',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'FTDWorld',
            'description': 'Free provider, less accurate. See <a href="http://ftdworld.net">FTDWorld</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
            ],
        },
    ],
}]
