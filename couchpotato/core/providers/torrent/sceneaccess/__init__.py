from .main import SceneAccess

def start():
    return SceneAccess()

config = [{
    'name': 'sceneaccess',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'SceneAccess',
            'description': 'See <a href="https://sceneaccess.eu/">SceneAccess</a>',
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
