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
                    'Label': 'Year',
                    'type': 'int',
                },
                {
                    'name': 'votes',
                    'default': 1000,
                    'Label': 'Votes',
                    'type': 'int',
                },
                {
                    'name': 'rating',
                    'default': 6.0,
                    'Label': 'Rating',
                    'type': 'float',
                },
            ],
        },
    ],
}]
