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
                    'name': 'seeding',
                    'label': 'Seeding support',
                    'default': True,
                    'type': 'bool',
                    'description': '(Hard)links/copies after download is complete (if enabled in renamer), wait for seeding to finish before (re)moving. Stop seeding manually in uTorrent, or check the option Queueing->When uTorrent reaches the seeding goal->Limit the upload rate and set it to 0 to stop seeding after the seeding goal set in the torrent providers is met.',
                },                
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': True,
                    'type': 'bool',
                    'description': 'Remove the torrent from uTorrent after it finished seeding.',
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
