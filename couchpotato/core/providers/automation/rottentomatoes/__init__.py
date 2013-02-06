from .main import Rottentomatoes

def start():
    return Rottentomatoes()

config = [{
    'name': 'rottentomatoes',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'rottentomatoes_automation',
            'label': 'Rottentomatoes',
            'description': 'Imports movies from the rottentomatoes "in theaters"-feed.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'tomatometer_percent',
                    'default': '80',
                    'label': 'Tomatometer'
                }
            ],
        },
    ],
}]
