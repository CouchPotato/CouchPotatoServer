from .main import rTorrent

def start():
    return rTorrent()

config = [{
    'name': 'rtorrent',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'rtorrent',
            'label': 'rTorrent',
            'description': '',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'torrent',
                },
# @RuudBurger: How do I migrate this?
#                {
#                    'name': 'url',
#                    'default': 'http://localhost:80/RPC2',
#                    'description': 'XML-RPC Endpoint URI. Usually <strong>scgi://localhost:5000</strong> '
#                                   'or <strong>http://localhost:80/RPC2</strong>'
#                },
                {
                    'name': 'host',
                    'default': 'localhost:80',
                    'description': 'Hostname with port or XML-RPC Endpoint URI. Usually <strong>scgi://localhost:5000</strong> '
                                   'or <strong>localhost:80</strong>'
                },
                {
                    'name': 'ssl',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use HyperText Transfer Protocol Secure, or <strong>https</strong>',
                },
                {
                    'name': 'rpc_url',
                    'type': 'string',
                    'default': 'RPC2',
                    'advanced': True,
                    'description': 'Change if you don\'t run rTorrent RPC at the default url.',
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
                    'description': 'Label to apply on added torrents.',
                },
                {
                    'name': 'directory',
                    'type': 'directory',
                    'description': 'Download to this directory. Keep empty for default rTorrent download directory.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': False,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the torrent after it finishes seeding.',
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
            ],
        }
    ],
}]
