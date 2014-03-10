from .main import PassThePopcorn


def start():
    return PassThePopcorn()

config = [{
    'name': 'passthepopcorn',
    'groups': [
        {
            'tab': 'searcher',
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
                    'name': 'prefer_golden',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer golden',
                    'default': 1,
                    'description': 'Favors Golden Popcorn-releases over all other releases.'
                },
                {
                    'name': 'prefer_scene',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Prefer scene',
                    'default': 0,
                    'description': 'Favors scene-releases over non-scene releases.'
                },
                {
                    'name': 'require_approval',
                    'advanced': True,
                    'type': 'bool',
                    'label': 'Require approval',
                    'default': 0,
                    'description': 'Require staff-approval for releases to be accepted.'
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
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
