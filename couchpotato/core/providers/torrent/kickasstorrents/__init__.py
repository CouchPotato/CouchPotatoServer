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
            'description': 'See <a href="https://kat.ph/">KickAssTorrents</a>',
            'wizard': True,
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
