from .main import Wizard


def start():
    return Wizard()

config = [{
    'name': 'core',
    'groups': [
        {
            'tab': 'general',
            'name': 'advanced',
            'options': [
                {
                    'name': 'show_wizard',
                    'label': 'Run the wizard',
                    'default': 1,
                    'type': 'bool',
                },
            ],
        },
    ],
}]
