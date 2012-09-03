from main import PassThePopcorn

def start():
    return PassThePopcorn()

config = [{
    'name': 'passthepopcorn',
    'groups': [{
        'tab': 'searcher',
        'subtab': 'providers',
        'name': 'PassThePopcorn',
        'description': 'See <a href="http://passthepopcorn.me">PassThePopcorn.me</a>',
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
                'description': 'Domain for requests (HTTPS only!), keep empty to use default (tls.passthepopcorn.me).',
            },
            {
                'name': 'username',
                'default': '',
            },
            {
                'name': 'password',
                'default': '',
                'type': 'password',
            }
        ],
    }]
}]
