from .main import XBMC

def start():
    return XBMC()

config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'xbmc',
            'label': 'XBMC',
            'description': 'v11 (Eden) and v12 (Frodo)',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                },
                {
                    'name': 'username',
                    'default': 'xbmc',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'only_first',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Only update the first host when movie snatched, useful for synced XBMC',
                },
                {
                    'name': 'remote_dir_scan',
                    'label': 'Remote Folder Scan',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Only scan new movie folder at remote XBMC servers. Works if movie location is the same.',
                },
                {
                    'name': 'force_full_scan',
                    'label': 'Always do a full scan',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Do a full scan instead of only the new movie. Useful if the XBMC path is different from the path CPS uses.',
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
