from .main import NMJ

def start():
    return NMJ()

config = [{
    'name': 'nmj',
    'groups': [
        {
            'tab': 'notifications',
            'name': 'nmj',
            'label': 'NMJ',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                    'description': '',
                },
                {
                    'name': 'database',
                    'default': '',
                    'description': '',
                },
                {
                    'name': 'mount',
                    'default': '',
                    'description': '',
                },
            ],
        }
    ],
}]
