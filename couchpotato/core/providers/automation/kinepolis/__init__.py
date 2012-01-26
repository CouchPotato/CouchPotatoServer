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
            'description': 'from <a href="http://kinepolis.be">Kinepolis</a>',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_use_requirements',
                    'label': 'Use requirements',
                    'description': 'Use the minimal requirements set above',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                },
            ],
        },
    ],
}]
