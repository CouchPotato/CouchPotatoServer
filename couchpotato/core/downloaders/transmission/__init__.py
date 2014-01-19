from .main import Transmission


def start():
    return Transmission()

config = [{
    'name': 'transmission',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
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
                    'name': 'rpc_url',
                    'type': 'string',
                    'default': 'transmission',
                    'advanced': True,
                    'description': 'Change if you don\'t run Transmission RPC at the default url.',
                },
                {
                    'name': 'username',
                },
                {
                    'name': 'password',
                    'type': 'password',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Download to this directory. Keep empty for default Transmission download directory.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent from Transmission after it finished seeding.',
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
                    'name': 'stalled_as_failed',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Consider a stalled torrent as failed',
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
