from .main import Moovee

def start():
    return Moovee()

config = [{
    'name': 'moovee',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': '#alt.binaries.moovee',
            'description': 'SD movies only',
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
