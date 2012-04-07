from .main import NzbIndex

def start():
    return NzbIndex()

config = [{
    'name': 'nzbindex',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'nzbindex',
            'description': 'Free provider, but less accurate.',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
