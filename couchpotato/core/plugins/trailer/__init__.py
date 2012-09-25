from .main import Trailer

def start():
    return Trailer()

config = [{
    'name': 'trailer',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'trailer',
            'label': 'Download trailer',
            'description': 'after rename',
            'options': [
                {
                    'name': 'enabled',
                    'label': 'Search and download trailers',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'quality',
                    'default': '720p',
                    'type': 'dropdown',
                    'values': [('1080P', '1080p'), ('720P', '720p'), ('480P', '480p')],
                },
                {
                    'name': 'automatic',
                    'default': False,
                    'type': 'bool',
                    'description': 'Automaticly search & download for movies in library',
                },
            ],
        },
    ],
}]
