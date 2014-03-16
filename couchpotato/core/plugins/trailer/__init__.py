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
                    'values': [('1080p', '1080p'), ('720p', '720p'), ('480P', '480p')],
                },
                {
                    'name': 'name',
                    'label': 'Naming',
                    'default': '<filename>-trailer',
                    'advanced': True,
                    'description': 'Use <strong>&lt;filename&gt;</strong> to use above settings.'
                },
            ],
        },
    ],
}]
