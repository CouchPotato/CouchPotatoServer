from .main import pyload


def start():
    return pyload()

config = [{
    'name': 'pyload',
    'groups': [
        {
            'tab': 'downloaders',
            'list': 'download_providers',
            'name': 'pyload',
            'label': 'pyload',
            'description': 'Use <a href="http://pyload.org/" target="_blank">pyload</a> (0.4.9+) to download files from OCH.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'OCH',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8000',
                    'description': 'Port can be found in settings when enabling WebUI.',
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
                    'description': 'Label to add download as.',
                },
                {
                    'name': 'wait_time',
                    'advanced': True,
                    'label': 'Wait Time',
                    'type': 'int',
                    'default': 90,
                    'description': 'Wait x seconds for post processing after files have finished downloading.',
                },
                {
                    'name': 'remove_complete',
                    'label': 'Remove torrent',
                    'default': True,
                    'advanced': True,
                    'type': 'bool',
                    'description': 'Remove the download link from pyload after it has finished downloading.',
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
                    'description': 'Add the download paused.',
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
                {
                    'name': 'download_collect',
                    'default': 1,
                    'advanced': True,
                    'type': 'dropdown',
                    'values': [('start downloading', 1), ('add to linkcollector', 0)],
                },
            ],
        }
    ],
}]


