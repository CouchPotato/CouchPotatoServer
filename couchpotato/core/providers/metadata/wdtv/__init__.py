from .main import WDTV

def start():
    return WDTV()
"""
config = [{
    'name': 'wdtv',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'wdtv_metadata',
            'label': 'WDTV',
            'description': 'Enable metadata WDTV can understand',
            'options': [
                {
                    'name': 'meta_enabled',
                    'default': False,
                    'type': 'enabler',
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
