from .main import SceneAccess

def start():
    return SceneAccess()

config = [{
    'name': 'sceneaccess',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'SceneAccess',
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
