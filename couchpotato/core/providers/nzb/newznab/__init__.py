from .main import Newznab

def start():
    return Newznab()

config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'searcher',
            'subtab': 'providers',
            'name': 'newznab',
            'description': 'Enable multiple NewzNab providers such as <a href="http://nzb.su" target="_blank">NZB.su</a>',
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
                    'default': 'nzb.su,dognzb.cr,beta.nzbs.org',
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
