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
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb',
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
                {
                    'name': 'category',
                    'label': 'Category',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'advanced': True,
                    'name': 'pp_directory',
                    'type': 'directory',
                    'description': 'Your Post-Processing Script directory, set in Sabnzbd > Config > Directories.',
                },
            ],
        }
    ],
}]
