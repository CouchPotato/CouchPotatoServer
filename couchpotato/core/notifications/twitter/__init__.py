from .main import Twitter


def start():
    return Twitter()

config = [{
    'name': 'twitter',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
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
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
                {
                    'name': 'direct_message',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use direct messages for the notifications (Also applies to the mentioned users).',
                },
            ],
        }
    ],
}]
