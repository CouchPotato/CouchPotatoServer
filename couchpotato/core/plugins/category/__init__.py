from .main import CategoryPlugin


def autoload():
    return CategoryPlugin()

config = [{
    'name': 'categories',
    'groups': [
        {
            'tab': 'searcher',
            'name': 'categories',
            'options': [
                {
                    'name': 'first_as_default',
                    'label': 'First as default',
                    'default': 0,
                    'type': 'bool',
                    'description': 'First category is selected by default.',
                },
            ],
        },
    ],
}]