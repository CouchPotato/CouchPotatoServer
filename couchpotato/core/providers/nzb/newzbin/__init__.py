from .main import Newzbin

def start():
    return Newzbin()

config = [{
    'name': 'newzbin',
    'groups': [
        {
            'tab': 'providers',
            'name': 'newzbin',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
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
