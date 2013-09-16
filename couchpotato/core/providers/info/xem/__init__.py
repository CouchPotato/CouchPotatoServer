from .main import Xem

def start():
    return Xem()

config = [{
    'name': 'xem',
    'groups': [
        {
            'tab': 'providers',
            'name': 'xem',
            'label': 'TheXem',
            'hidden': True,
            'description': 'Used for all calls to TheXem.',
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'label': 'Enabled',
                },
            ],
        },
    ],
}]
