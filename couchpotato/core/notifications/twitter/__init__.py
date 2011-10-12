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
                    'name': 'access_token_key',
                    'advanced': True,
                },
                {
                    'name': 'screen_name',
                    'advanced': True,
                },
                {
                    'name': 'access_token_secret',
                    'advanced': True,
                },
                {
                    'name': 'mention',
                    'description': 'Add a mention to this user to the tweet.',
                },
            ],
        }
    ],
}]
