from couchpotato.core.providers.och.hdworld.main import hdworld


def start():
    return hdworld()

config = [{
    'name': 'hdworld',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'och_providers',
            'name': 'HD-World',
            'description': 'See <a href="https://www.hd-world.org">HD-World.org</a>',
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
                {
                    'name': 'hosters',
                    'label': 'accepted Hosters',
                    'default': '',
                    'placeholder': 'Example: uploaded,share-online',
                    'description': 'List of Hosters separated by ",". Should be at least one!'
                },
            ],
        },
    ],
}]
