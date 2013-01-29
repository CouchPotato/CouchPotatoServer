from main import Deildu

def start():
    return Deildu()

config = [{
    'name': 'deildu',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'Deildu.net',
            'description': 'See <a href="http://deildu.net">Deildu.net</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                }
            ],
        }
    ]
}]
