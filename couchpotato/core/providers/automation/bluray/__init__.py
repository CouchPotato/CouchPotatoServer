from .main import Bluray

def start():
    return Bluray()

config = [{
    'name': 'bluray',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'bluray_automation',
            'label': 'Blu-ray.com',
            'description': 'Imports movies from blu-ray.com.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'backlog',
                    'advanced': True,
                    'description': 'Parses the history until the minimum movie year is reached. (Will be disabled once it has completed)',
                    'default': False,
                    'type': 'bool',
                },
            ],
        },
        {
            'tab': 'display',
            'list': 'charts_providers',
            'name': 'bluray_charts_display',
            'label': 'Blu-ray.com',
            'description': 'Display new releases from Blu-ray.com',
            'options': [
                {
                    'name': 'chart_display_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
