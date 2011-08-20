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
            'description': 'Download the NZB/Torrent to a specific folder.',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .nzb (or .torrent) file is saved to.',
                },
            ],
        }
    ],
}]
