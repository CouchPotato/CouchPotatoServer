from .main import Aria2


def start():
    return Aria2()

config = [{
    'name': 'aria2',
    'groups': [
        {
            'tab': 'downloaders',
            'name': 'aria2',
            'label': 'aria2',
            'description': 'Send download URLs to aria2.',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                    'radio_group': 'http',
                },
                {
                    'name': 'host',
                    'default': 'htpc:6800',
                },
                {
                    'name': 'manual',
                    'default': True,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Disable this downloader for automated searches, but use it when I manually send a release.',
                },
                {
                    'name': 'delete_failed',
                    'default': False,
                    'type': 'bool',
                    'description': 'Delete a release after the download has failed.',
                },
            ],
        }
    ],
}]
