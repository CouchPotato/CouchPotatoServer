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
                    'name': 'replace_folder',
                    'label': 'Replace folder base',
                    'advanced': True,
                    'placeholder': 'Example: /home/, X:\\',
                    'description': 'Replace the first folder base with the second in downloaded movie paths. Use if the downloader is on a different computer to convert the paths.',
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
