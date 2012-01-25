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
            'description': 'Enable automatic movie adding from Kinepolis',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls',
                },
            ],
        },
    ],
}]
