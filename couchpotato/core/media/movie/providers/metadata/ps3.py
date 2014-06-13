import os

from couchpotato.core.media.movie.providers.metadata.base import MovieMetaData


autoload = 'SonyPS3'


class SonyPS3(MovieMetaData):

    def getThumbnailName(self, name, root, i):
        return os.path.join(root, 'cover.jpg')


config = [{
    'name': 'sonyps3',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'sonyps3_metadata',
            'label': 'Sony PS3',
            'description': 'Generate cover.jpg',
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
