from .main import X264

def start():
    return X264()

config = [{
    'name': 'x264',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': '#alt.binaries.hdtv.x264',
            'description': 'HD movies only',
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
