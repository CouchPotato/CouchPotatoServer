from .main import Kinepolis

def start():
    return Kinepolis()

config = [{
    'name': 'kinepolis',
    'groups': [
        {
            'tab': 'automation',
            'name': 'kinepolis_automation',
            'label': 'Kinepolis',
            'description': 'imports movies from the current top 10 of kinepolis',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]