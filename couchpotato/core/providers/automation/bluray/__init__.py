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
            'description': 'imports movies from blu-ray.com',
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