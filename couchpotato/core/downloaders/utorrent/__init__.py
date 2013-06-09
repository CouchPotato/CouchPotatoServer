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
            'description': 'Use <a href="http://www.utorrent.com/" target="_blank">uTorrent</a> to download torrents.',
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
                    'name': 'archivelabel',
                    'description': 'Label to keep torrent.',
                },
                {
                    'name': 'paused',
                    'type': 'bool',
                    'default': False,
                    'description': 'Add the torrent paused.',
                },
                {
                    'name': 'waitseeding',
                    'type': 'bool',
                    'default': False,
                    'description': 'Wait end of seeding before doing anything.',
                },
                {
                    'name': 'autostop',
                    'type': 'bool',
                    'default': False,
                    'description': 'Stop the torrent in uTorrent at end of seeding. (waitseeding required)',
                },
                {
                    'name': 'autoremove',
                    'type': 'bool',
                    'default': False,
                    'description': 'Remove the torrent from uTorrent at end of seeding. (waitseeding & autostop required)',
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
