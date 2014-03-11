from couchpotato.core.media.movie.providers.metadata.base import MovieMetaData
import os


class WindowsMediaCenter(MovieMetaData):

    def getThumbnailName(self, name, root):
        return os.path.join(root, 'folder.jpg')
