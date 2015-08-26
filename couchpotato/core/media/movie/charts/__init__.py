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
            'options': [],
        },
    ],
}]
