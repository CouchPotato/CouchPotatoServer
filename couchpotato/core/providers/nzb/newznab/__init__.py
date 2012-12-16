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
            'description': 'Enable <a href="http://newznab.com/" target="_blank">NewzNab providers</a> such as <a href="https://nzb.su" target="_blank">NZB.su</a>, \
                <a href="https://nzbs.org" target="_blank">NZBs.org</a>, <a href="http://dognzb.cr/" target="_blank">DOGnzb.cr</a>, \
                <a href="https://github.com/spotweb/spotweb" target="_blank">Spotweb</a>',
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
