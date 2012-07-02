from .main import Bluray

def start():
    return Bluray()

config = [{
    'name': 'bluray',
    'groups': [
        {
            'tab': 'automation',
            'name': 'bluray_automation',
            'label': 'Blu-ray.com',
            'description': 'Imports movies from blu-ray.com. (uses minimal requirements)',
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
