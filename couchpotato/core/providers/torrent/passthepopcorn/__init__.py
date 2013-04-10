from main import PassThePopcorn

def start():
    return PassThePopcorn()

config = [{
    'name': 'passthepopcorn',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'list': 'torrent_providers',
            'name': 'PassThePopcorn',
            'description': 'See <a href="https://passthepopcorn.me">PassThePopcorn.me</a>',
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
                },
                {
                    'name': 'passkey',
                    'default': '',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
}
    ]
}]
