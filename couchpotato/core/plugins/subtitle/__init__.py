from .main import Subtitle

def start():
    return Subtitle()

config = [{
    'name': 'subtitle',
    'groups': [
        {
            'tab': 'renamer',
            'name': 'subtitle',
            'options': [
                {
                    'name': 'enabled',
                    'label': 'Search and download subtitles',
                    'default': True,
                    'type': 'enabler',
                },
                {
                    'name': 'languages',
                    'description': 'The languages you want to download the sub',
                },
                {
                    'name': 'automatic',
                    'default': True,
                    'type': 'bool',
                    'description': 'Automaticly search & download for movies in library',
                },
            ],
        },
    ],
}]
