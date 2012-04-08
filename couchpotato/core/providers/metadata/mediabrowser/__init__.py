from .main import MediaBrowser

def start():
    return MediaBrowser()

"""
config = [{
    'name': 'mediabrowser',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'mediabrowser_metadata',
            'label': 'MediaBrowser',
            'description': 'Enable metadata MediaBrowser can understand',
            'options': [
                {
                    'name': 'meta_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'meta_nfo',
                    'default': True,
                    'type': 'bool',
                },
                {
                    'name': 'meta_fanart',
                    'default': True,
                    'type': 'bool',
                },
                {
                    'name': 'meta_thumbnail',
                    'default': True,
                    'type': 'bool',
                },
            ],
        },
    ],
}]
"""
