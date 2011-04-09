from .main import Sabnzbd

def start():
    return Sabnzbd()

config = [{
    'name': 'sabnzbd',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'sabnzbd',
            'label': 'Sabnzbd',
            'description': 'Fill in your Sabnzbd settings.',
            'options': [
                {
                    'name': 'enabled',
                    'default': False,
                    'type': 'bool',
                    'label': 'Enabled',
                    'description': 'Send snatched NZBs to Sabnzbd',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                    'type': 'string',
                    'label': 'Host',
                    'description': 'Test',
                },
                {
                    'name': 'api_key',
                    'default': '',
                    'type': 'string',
                    'label': 'Api Key',
                    'description': 'Used for all calls to Sabnzbd.',
                },
            ],
        }
    ],
}]
