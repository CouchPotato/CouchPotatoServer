from .main import PutIO


def autoload():
    return PutIO()


config = [{
    'name': 'putio',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'putio',
            'label': 'Put.io',
            'description': 'This will start a torrent download on <a href="https://put.io/" target="_blank">Put.io</a>.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
                {
                    'name': 'oauth_token',
                    'label': 'oauth_token',
                    'description': 'This is the OAUTH_TOKEN from your putio API',
                    'advanced': True,
                },
                {
                    'name': 'folder',
                    'description': ('The folder on putio where you want the upload to go','Will find the first first folder that matches this name'),
                    'default': 0,
                },
                {
                    'name': 'https',
                    'description': 'Set to true if your callback host accepts https instead of http',
                    'type': 'bool',
                    'default': 0,
                },
                {
                    'name': 'callback_host',
                    'description': 'External reachable url to CP so put.io can do it\'s thing',
                },
                {
                    'name': 'download',
                    'description': 'Set this to have CouchPotato download the file from Put.io',
                    'type': 'bool',
                    'default': 0,
                },
                {
                    'name': 'delete_file',
                    'description': ('Set this to remove the file from putio after sucessful download','Does nothing if you don\'t select download'),
                    'type': 'bool',
                    'default': 0,
                },
                {
                    'name': 'download_dir',
                    'type': 'directory',
                    'label': 'Download Directory',
                    'description': 'The Directory to download files to, does nothing if you don\'t select download',
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
