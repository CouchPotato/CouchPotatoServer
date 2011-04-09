from .main import Blackhole

def start():
    return Blackhole()

config = [{
    'name': 'blackhole',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'blackhole',
            'label': 'Black hole',
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
                    'name': 'directory',
                    'default': '',
                    'type': 'directory',
                    'label': 'Directory',
                    'description': 'Directory where the .nzb (or .torrent) file is saved to.',
                },
            ],
        }
    ],
}]
