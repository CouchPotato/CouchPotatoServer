from .main import OMGWTFNZBs

def start():
    return OMGWTFNZBs()

config = [{
    'name': 'omgwtfnzbs',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'OMGWTFNZBs',
            'description': 'See <a href="http://www.omgwtfnzbs.com/">OMGWTFNZBs</a>',
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
