import os

from couchpotato.core.media.movie.providers.metadata.base import MovieMetaData


autoload = 'MediaBrowser'


class MediaBrowser(MovieMetaData):

    def getThumbnailName(self, name, root, i):
        return os.path.join(root, 'folder.jpg')

    def getFanartName(self, name, root, i):
        return os.path.join(root, 'backdrop.jpg')


config = [{
    'name': 'mediabrowser',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'mediabrowser_metadata',
            'label': 'MediaBrowser',
            'description': 'Generate folder.jpg and backdrop.jpg',
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
