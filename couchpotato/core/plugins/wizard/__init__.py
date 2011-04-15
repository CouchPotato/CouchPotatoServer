from .main import Wizard

def start():
    return Wizard()

config = [{
    'name': 'global',
    'groups': [
        {
            'tab': 'general',
            'name': 'advanced',
            'options': [
                {
                    'name': 'show_wizard',
                    'label': 'Run the wizard',
                    'default': True,
                    'type': 'bool',
                },
            ],
        },
    ],
}]
