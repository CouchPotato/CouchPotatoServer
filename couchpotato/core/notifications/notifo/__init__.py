from .main import Notifo

def start():
    return Notifo()

config = [{
    'name': 'notifo',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'notifo',
            'description': '',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'default': '',
                    'type': 'string',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
            ],
        }
    ],
}]
