from .main import Newznab

def start():
    return Newznab()

config = [{
    'name': 'newznab',
    'groups': [
        {
            'tab': 'providers',
            'name': 'newznab',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
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
                    'description': 'Can be found after login on the "API" page, bottom left. The string after "&amp;apikey=".',
                },
            ],
        },
    ],
}]
