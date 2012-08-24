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
            'description': 'Free provider, less accurate. See <a href="http://www.nzbindex.nl/">NZBIndex</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
