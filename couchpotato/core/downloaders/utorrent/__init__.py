from .main import uTorrent

def start():
    return uTorrent()

config = [{
    'name': 'utorrent',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'utorrent',
            'label': 'uTorrent',
            'description': 'Use <a href="http://www.utorrent.com/" target="_blank">uTorrent</a> (3.0+) to download torrents.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8000',
                    'description': 'Hostname with port. Usually <strong>localhost:8000</strong>',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'label',
                    'description': 'Label to add torrent as.',
                },
                {
                    'name': 'download_directory',
                    'type': 'dropdown',
                    'advanced': True,
                    'values': [ ('Default Directory','Default Directory') ],
                    'description': 'Download to this directory. Folders must be set-up in uTorrent client to appear here.',
                },
                {
                    'name': 'download_subpath',
                    'advanced': True,
                    'description': 'Download directory sub-path.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent from uTorrent after it finished seeding.',
                },
                {
                    'name': 'delete_files',
                    'label': 'Remove files',
                    'default': True,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also remove the leftover files.',
                },
                {
                    'name': 'paused',
                    'type': 'bool',
                    'advanced': True,
                    'default': False,
                    'description': 'Add the torrent paused.',
                },
                {
                    'name': 'manual',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
                {
                    'name': 'delete_failed',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Delete a release after the download has failed.',
                },
            ],
        }
    ],
}]
