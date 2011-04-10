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
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost',
                },
                {
                    'name': 'database',
                },
                {
                    'name': 'mount',
                },
            ],
        }
    ],
}]
