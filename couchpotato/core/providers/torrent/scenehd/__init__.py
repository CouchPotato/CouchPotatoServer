from .main import SceneHD

def start():
    return SceneHD()

config = [{
    'name': 'scenehd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'SceneHD',
            'description': 'See <a href="https://scenehd.org">SceneHD</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
            ],
        },
    ],
}]
