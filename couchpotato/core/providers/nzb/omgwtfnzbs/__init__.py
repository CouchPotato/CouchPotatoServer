from .main import OMGWTFNZBs

def start():
    return OMGWTFNZBs()

config = [{
    'name': 'omgwtfnzbs',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
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
            ],
        },
    ],
}]
