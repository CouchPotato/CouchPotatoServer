from .main import SceneAccess

def start():
    return SceneAccess()

config = [{
    'name': 'sceneaccess',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'torrent_providers',
            'name': 'SceneAccess',
            'description': 'See <a href="https://sceneaccess.eu/">SceneAccess</a>',
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
