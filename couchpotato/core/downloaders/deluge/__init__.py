from .main import Deluge

def start():
    return Deluge()

config = [{
    'name': 'deluge',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'deluge',
            'label': 'Deluge',
            'description': 'Use <a href="http://www.deluge-torrent.org/" target="_blank">Deluge</a> to download torrents.',
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
                    'default': 'localhost:58846',
                    'description': 'Hostname with port. Usually <strong>localhost:58846</strong>',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'paused',
                    'type': 'bool',
                    'default': False,
                    'description': 'Add the torrent paused.',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Download to this directory. Keep empty for default Deluge download directory.',
                },
                {
                    'name': 'completed_directory',
                    'type': 'directory',
                    'description': 'Move completed torrent to this directory. Keep empty for default Deluge options.',
                    'advanced': True,
                },
                {
                    'name': 'label',
                    'description': 'Label to add to torrents in the Deluge UI.',
                },
                {
                    'name': 'ratio',
                    'default': 10,
                    'type': 'float',
                    'advanced': True,
                    'description': 'Stop transfer when reaching ratio',
                },
                {
                    'name': 'ratioremove',
                    'type': 'bool',
                    'default': False,
                    'advanced': True,
                    'description': 'Remove torrent when ratio reached.',
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
