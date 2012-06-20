from .main import SceneHD

def start():
    return SceneHD()

config = [{
    'name': 'scenehd',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'SceneHD',
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
