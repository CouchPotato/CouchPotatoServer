from .main import NZBClub

def start():
    return NZBClub()

config = [{
    'name': 'nzbclub',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'NZBClub',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbclub.com/">NZBClub</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
