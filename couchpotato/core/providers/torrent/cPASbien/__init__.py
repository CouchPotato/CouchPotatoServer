from .main import cPASbien

def start():
    return cPASbien()

config = [{
    'name': 'cPASbien',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'cPASbien',
            'description': 'See <a href="http://www.cpasbien.com/">cPASbien</a>',
            'wizard': True,
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
