from .main import NzbIndex

def start():
    return NzbIndex()

config = [{
    'name': 'nzbindex',
    'groups': [
        {
            'tab': 'providers',
            'name': 'nzbindex',
            'description': 'Free provider, but less accurate.',
            'advanced': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
