from .main import Nzbx

def start():
    return Nzbx()

config = [{
    'name': 'nzbx',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'nzbx',
            'description': 'Free provider, less accurate. See <a href="https://www.nzbx.co/">nzbx</a>',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True,
                },
            ],
        },
    ],
}]
