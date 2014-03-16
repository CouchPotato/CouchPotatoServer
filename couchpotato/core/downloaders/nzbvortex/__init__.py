from .main import NZBVortex


def start():
    return NZBVortex()

config = [{
    'name': 'nzbvortex',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'nzbvortex',
            'label': 'NZBVortex',
            'description': 'Use <a href="http://www.nzbvortex.com/landing/" target="_blank">NZBVortex</a> to download NZBs.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'nzb',
                },
                {
                    'name': 'host',
                    'default': 'localhost:4321',
                    'description': 'Hostname with port. Usually <strong>localhost:4321</strong>',
                },
                {
                    'name': 'ssl',
                    'default': 1,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use HyperText Transfer Protocol Secure, or <strong>https</strong>',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                },
                {
                    'name': 'manual',
                    'default': False,
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
