from .main import Newznab

def start():
    return Newznab()

config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'nzb_providers',
            'name': 'newznab',
            'order': 10,
            'description': 'Enable multiple NewzNab providers such as <a href="https://nzb.su" target="_blank">NZB.su</a> and <a href="https://nzbs.org" target="_blank">nzbs.org</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'use',
                    'default': '0,0,0'
                },
                {
                    'name': 'host',
                    'default': 'nzb.su,dognzb.cr,nzbs.org',
                    'description': 'The hostname of your newznab provider',
                },
                {
                    'name': 'api_key',
                    'default': ',,',
                    'label': 'Api Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'api_key'],
                },
            ],
        },
    ],
}]
