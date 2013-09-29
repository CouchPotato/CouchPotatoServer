from .main import rTorrent

def start():
    return rTorrent()

config = [{
    'name': 'rtorrent',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'rtorrent',
            'label': 'rTorrent',
            'description': '',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'url',
                    'default': 'http://localhost:80/RPC2',
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
                    'description': 'Label to apply on added torrents.',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Directory where rtorrent should download the files too.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': False,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent after it finishes seeding.',
                },
                {
                    'name': 'append_label',
                    'label': 'Append Label',
                    'default': False,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Append label to download location. Requires you to set the download location above.',
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
            ],
        }
    ],
}]
