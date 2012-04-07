from .main import XBMC

def start():
    return XBMC()

config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'xbmc_metadata',
            'label': 'XBMC',
            'description': 'Enable metadata XBMC can understand',
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
