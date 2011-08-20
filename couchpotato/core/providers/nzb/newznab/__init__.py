from .main import Newznab

def start():
    return Newznab()

config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'providers',
            'name': 'newznab',
            'description': 'Enable multiple NewzNab providers',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'use',
                    'default': '0'
                },
                {
                    'name': 'host',
                    'default': 'http://nzb.su',
                    'description': 'The hostname of your newznab provider, like http://nzb.su'
                },
                {
                    'name': 'api_key',
                    'default': '',
                    'label': 'Api Key',
                    'description': 'Can be found on your profile page',
                },
            ],
        },
    ],
}]
