from .main import BinSearch

def start():
    return BinSearch()

config = [{
    'name': 'binsearch',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'binsearch',
            'description': 'Free provider, less accurate. See <a href="https://www.binsearch.info/">BinSearch</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
