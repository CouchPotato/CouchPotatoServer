from .main import Sabnzbd

def start():
    return Sabnzbd()

config = [{
    'name': 'sabnzbd',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'sabnzbd',
            'label': 'Sabnzbd',
            'description': 'Use <a href="http://sabnzbd.org/" target="_blank">SABnzbd</a> to download NZBs.',
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
                    'default': 'localhost:8080',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'description': 'Used for all calls to Sabnzbd.',
                },
                {
                    'name': 'category',
                    'label': 'Category',
                    'description': 'The category CP places the nzb in. Like <strong>movies</strong> or <strong>couchpotato</strong>',
                },
                {
                    'name': 'replace_folder',
                    'label': 'Replace folder base',
                    'advanced': True,
                    'placeholder': 'Example: /home/, X:\\',
                    'description': 'Replace the first folder base with the second in downloaded movie paths. Use if the downloader is on a different computer to convert the paths.',
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
                    'type': 'bool',
                    'description': 'Delete a release after the download has failed.',
                },
            ],
        }
    ],
}]
