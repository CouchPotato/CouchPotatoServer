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
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'type': 'bool',
                    'default': True,
                    'advanced': True,
                    'description': 'Remove the torrent from Deluge after it has finished seeding.',
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
