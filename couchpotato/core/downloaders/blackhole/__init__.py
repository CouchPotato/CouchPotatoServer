from .main import Blackhole

def start():
    return Blackhole()

config = [{
    'name': 'blackhole',
    'order': 30,
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'blackhole',
            'label': 'Black hole',
            'description': 'Download the NZB/Torrent to a specific folder.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb,torrent',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .nzb (or .torrent) file is saved to.',
                },
                {
                    'name': 'use_for',
                    'label': 'Use for',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'nzb'), ('torrent', 'torrent')],
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
