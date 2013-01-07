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
            'description': 'Use <a href="http://www.synology.com/dsm/home_home_applications_download_station.php" target="_blank">Synology Download Station</a> to download.',
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
