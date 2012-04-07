from .main import KickAssTorrents

def start():
    return KickAssTorrents()

config = [{
    'name': 'kickasstorrents',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'KickAssTorrents',
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
