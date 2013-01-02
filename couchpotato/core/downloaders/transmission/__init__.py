from .main import Transmission

def start():
    return Transmission()

config = [{
    'name': 'transmission',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'transmission',
            'label': 'Transmission',
            'description': 'Use <a href="http://www.transmissionbt.com/" target="_blank">Transmission</a> to download torrents.',
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
                    'default': 'localhost:9091',
                    'description': 'Hostname with port. Usually <strong>localhost:9091</strong>',
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
                    'description': 'Where should Transmission saved the downloaded files?',
                },
                {
                    'name': 'ratio',
                    'default': 10,
                    'type': 'int',
                    'advanced': True,
                    'description': 'Stop transfer when reaching ratio',
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
