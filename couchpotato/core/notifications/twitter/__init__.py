from .main import Twitter

def start():
    return Twitter()

config = [{
    'name': 'twitter',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'twitter',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'advanced': True,
                },
                {
                    'name': 'password',
                    'advanced': True,
                },
            ],
        }
    ],
}]
