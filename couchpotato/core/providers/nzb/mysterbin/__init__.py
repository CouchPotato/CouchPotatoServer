from .main import Mysterbin

def start():
    return Mysterbin()

config = [{
    'name': 'mysterbin',
    'groups': [
        {
            'tab': 'providers',
            'name': 'Mysterbin',
            'description': '',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
            ],
        },
    ],
}]
