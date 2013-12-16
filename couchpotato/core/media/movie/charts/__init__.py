from .main import Charts

def start():
    return Charts()

config = [{
    'name': 'charts',
    'groups': [
        {
            'label': 'Charts',
            'description': 'Displays selected charts on the home page',
            'type': 'list',
            'name': 'charts_providers',
            'tab': 'display',
            'options': [
                {
                    'name': 'max_items',
                    'default': 5,
                    'type': 'int',
                    'description': 'Maximum number of items displayed for each chart.',
                },
                {
                    'name': 'update_interval',
                    'default': 12,
                    'type': 'int',
                    'advanced': True,
                    'description': '(hours)',
                },
            ],
        },
    ],
}]
