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
            'description': 'Send NZBs to your Sabnzbd installation.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'description': 'Used for all calls to Sabnzbd.',
                },
            ],
        }
    ],
}]
