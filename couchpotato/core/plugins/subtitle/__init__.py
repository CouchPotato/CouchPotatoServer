from .main import Subtitle

def start():
    return Subtitle()

config = [{
    'name': 'subtitle',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'subtitle',
            'label': 'Download subtitles',
            'description': 'after rename',
            'options': [
                {
                    'name': 'enabled',
                    'label': 'Search and download subtitles',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'languages',
                    'description': 'Comma separated, 2 letter country code. Example: en, nl',
                },
#                {
#                    'name': 'automatic',
#                    'default': True,
#                    'type': 'bool',
#                    'description': 'Automaticly search & download for movies in library',
#                },
            ],
        },
    ],
}]
