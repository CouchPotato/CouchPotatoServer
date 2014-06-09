import os

from couchpotato.core.media.movie.providers.metadata.base import MovieMetaData


autoload = 'WindowsMediaCenter'


class WindowsMediaCenter(MovieMetaData):

    def getThumbnailName(self, name, root, i):
        return os.path.join(root, 'folder.jpg')


config = [{
    'name': 'windowsmediacenter',
    'groups': [
        {
            'tab': 'renamer',
            'subtab': 'metadata',
            'name': 'windowsmediacenter_metadata',
            'label': 'Windows Explorer / Media Center',
            'description': 'Generate folder.jpg',
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
