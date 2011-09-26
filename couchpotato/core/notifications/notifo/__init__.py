from .main import Notifo

def start():
    return Notifo()

config = [{
    'name': 'notifo',
    'groups': [
        {
            'tab': 'notifications',
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
                    'name': 'password',
                    'type': 'password',
                },
            ],
        }
    ],
}]
