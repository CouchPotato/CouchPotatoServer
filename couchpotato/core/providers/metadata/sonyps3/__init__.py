from .main import SonyPS3

def start():
    return SonyPS3()

"""
config = [{
    'name': 'sonyps3',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'sonyps3_metadata',
            'label': 'Sony PS3',
            'description': 'Enable metadata your Playstation 3 can understand',
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
