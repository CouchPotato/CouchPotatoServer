from couchpotato.core.providers.och.funxd.main import funxd


def start():
    return funxd()

config = [{
    'name': 'funxd',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'och_providers',
            'name': 'FunXD.in',
            'description': 'See <a href="https://www.funxd.in">funXD.in</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                },
            ],
        },
    ],
}]
