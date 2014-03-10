from .main import OMGWTFNZBs


def start():
    return OMGWTFNZBs()

config = [{
    'name': 'omgwtfnzbs',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'OMGWTFNZBs',
            'description': 'See <a href="http://omgwtfnzbs.org/">OMGWTFNZBs</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'default': '',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': 20,
                    'type': 'int',
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
