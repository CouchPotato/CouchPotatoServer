from main import ThePirateBay

def start():
    return ThePirateBay()

config = [{
    'name': 'thepiratebay',
    'groups': [{
        'tab': 'searcher',
        'subtab': 'providers',
        'name': 'ThePirateBay',
        'description': 'The world\'s largest bittorrent tracker. See <a href="http://fucktimkuik.org/">ThePirateBay</a>',
        'wizard': True,
        'options': [
            {
                'name': 'enabled',
                'type': 'enabler',
                'default': False
            },
            {
                'name': 'domain',
                'advanced': True,
                'label': 'Proxy server',
                'description': 'Domain for requests, keep empty to let CouchPotato pick.',
            }
        ],
    }]
}]
