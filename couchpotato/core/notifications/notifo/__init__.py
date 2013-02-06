from .main import Notifo

def start():
    return Notifo()

config = [{
    'name': 'notifo',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'notifo',
            'description': 'Keep in mind that Notifo service will end soon.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'api_key',
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
