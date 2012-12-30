from .main import Moviemeter

def start():
    return Moviemeter()

config = [{
    'name': 'moviemeter',
    'groups': [
        {
            'tab': 'automation',
            'name': 'moviemeter_automation',
            'label': 'Moviemeter',
            'description': 'Imports movies from the current top 10 of moviemeter.nl. (uses minimal requirements)',
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
