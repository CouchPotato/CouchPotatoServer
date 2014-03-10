from couchpotato.core.providers.metadata.base import MetaDataBase
import os


class WindowsMediaCenter(MetaDataBase):

    def getThumbnailName(self, name, root):
        return os.path.join(root, 'folder.jpg')
