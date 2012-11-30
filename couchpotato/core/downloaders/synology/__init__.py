from .main import Synology

def start():
    return Synology()

config = [{
    'name': 'synology',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'synology',
            'label': 'Synology',
            'description': 'Send torrents to Synology\'s Download Station.',
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
                    'default': 'localhost:5000',
                    'description': 'Hostname with port. Usually <strong>localhost:5000</strong>',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
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
