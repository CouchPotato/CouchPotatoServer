from .main import Automation

def start():
    return Automation()

config = [{
    'name': 'automation',
    'groups': [
        {
            'tab': 'automation',
            'name': 'automation',
            'label': 'Automation',
            'description': 'Enable automatic movie adding',
            'options': [
                {
                    'name': 'year',
                    'default': 2011,
                    'Label': 'Minimal year',
                    'type': 'int',
                },
                {
                    'name': 'votes',
                    'default': 1000,
                    'Label': 'Minimal votes',
                    'type': 'int',
                },
                {
                    'name': 'rating',
                    'default': 6.0,
                    'Label': 'Minimal rating',
                    'type': 'float',
                },
            ],
        },
    ],
}]
