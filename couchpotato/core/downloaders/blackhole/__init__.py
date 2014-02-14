from .main import Blackhole
from couchpotato.core.helpers.variable import getDownloadDir


def start():
    return Blackhole()

config = [{
    'name': 'blackhole',
    'order': 30,
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'blackhole',
            'label': 'Black hole',
            'description': 'Download the NZB/Torrent to a specific folder. <em>Note: Seeding and copying/linking features do <strong>not</strong> work with Black hole</em>.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': True,
                    'type': 'enabler',
                    'radio_group': 'nzb,torrent',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where the .nzb (or .torrent) file is saved to.',
                    'default': getDownloadDir()
                },
                {
                    'name': 'use_for',
                    'label': 'Use for',
                    'default': 'both',
                    'type': 'dropdown',
                    'values': [('usenet & torrents', 'both'), ('usenet', 'nzb'), ('torrent', 'torrent')],
                },
                {
                    'name': 'create_subdir',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Create a sub directory when saving the .nzb (or .torrent).',
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
