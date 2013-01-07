from .main import uTorrent

def start():
    return uTorrent()

config = [{
    'name': 'utorrent',
    'groups': [
        {
            'tab': 'downloaders',
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
                    'name': 'paused',
                    'type': 'bool',
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
