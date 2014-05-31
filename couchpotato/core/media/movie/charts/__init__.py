from .main import Charts


def autoload():
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
                    'description': 'Maximum number of items displayed from each chart.',
                },
                {
                    'name': 'update_interval',
                    'default': 12,
                    'type': 'int',
                    'advanced': True,
                    'description': '(hours)',
                },
                {
                    'name': 'hide_wanted',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Hide the chart movies that are already in your wanted list.',
                },
                {
                    'name': 'hide_library',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Hide the chart movies that are already in your library.',
                },
            ],
        },
    ],
}]
