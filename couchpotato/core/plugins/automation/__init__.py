from .main import Automation

def start():
    return Automation()

config = [{
    'name': 'automation',
    'order': 30,
    'groups': [
        {
            'tab': 'automation',
            'name': 'automation',
            'label': 'Automation',
            'description': 'Minimal movie requirements',
            'options': [
                {
                    'name': 'year',
                    'default': 2011,
                    'type': 'int',
                },
                {
                    'name': 'votes',
                    'default': 1000,
                    'type': 'int',
                },
                {
                    'name': 'rating',
                    'default': 7.0,
                    'type': 'float',
                },
                {
                    'name': 'hour',
                    'advanced': True,
                    'default': 12,
                    'label': 'Check every',
                    'type': 'int',
                    'unit': 'hours',
                    'description': 'hours',
                },
            ],
        },
    ],
}]
