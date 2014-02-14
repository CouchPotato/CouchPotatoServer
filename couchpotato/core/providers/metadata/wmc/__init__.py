from .main import WindowsMediaCenter


def start():
    return WindowsMediaCenter()

config = [{
    'name': 'windowsmediacenter',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'windowsmediacenter_metadata',
            'label': 'Windows Explorer / Media Center',
            'description': 'Generate folder.jpg',
            'options': [
                {
                    'name': 'meta_enabled',
                    'default': False,
                    'type': 'enabler',
                },
            ],
        },
    ],
}]
