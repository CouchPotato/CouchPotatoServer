from .main import Mysterbin

def start():
    return Mysterbin()

config = [{
    'name': 'mysterbin',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'Mysterbin',
            'description': 'Free provider, less accurate. See <a href="http://www.mysterbin.com/">Mysterbin</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
            ],
        },
    ],
}]
