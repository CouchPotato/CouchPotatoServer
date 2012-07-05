from .main import Pneumatic

def start():
    return Pneumatic()

config = [{
    'name': 'pneumatic',
    'order': 30,
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'pneumatic',
            'label': 'Pneumatic',
            'description': 'Download the .strm file to a specific folder.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .strm file is saved to.',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
            ],
        }
    ],
}]
