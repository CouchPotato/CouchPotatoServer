from .main import NZBClub

def start():
    return NZBClub()

config = [{
    'name': 'nzbclub',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'NZBClub',
            'description': '',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
            ],
        },
    ],
}]
