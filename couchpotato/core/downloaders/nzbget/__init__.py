from .main import NZBGet


def start():
    return NZBGet()

config = [{
    'name': 'nzbget',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'nzbget',
            'label': 'NZBGet',
            'description': 'Use <a href="http://nzbget.sourceforge.net/Main_Page" target="_blank">NZBGet</a> to download NZBs.',
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
                    'default': 'localhost:6789',
                    'description': 'Hostname with port. Usually <strong>localhost:6789</strong>',
                },
                {
                    'name': 'ssl',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Use HyperText Transfer Protocol Secure, or <strong>https</strong>',
                },
                {
                    'name': 'username',
                    'default': 'nzbget',
                    'advanced': True,
                    'description': 'Set a different username to connect. Default: nzbget',
                },
                {
                    'name': 'password',
                    'type': 'password',
                    'description': 'Default NZBGet password is <i>tegbzn6789</i>',
                },
                {
                    'name': 'category',
                    'default': 'Movies',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'name': 'priority',
                    'advanced': True,
                    'default': '0',
                    'type': 'dropdown',
                    'values': [('Very Low', -100), ('Low', -50), ('Normal', 0), ('High', 50), ('Very High', 100)],
                    'description': 'Only change this if you are using NZBget 9.0 or higher',
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
