import os
import shutil
import traceback

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import sp
from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.metadata.base import MetaDataBase
from couchpotato.environment import Env


log = CPLog(__name__)


class MovieMetaData(MetaDataBase):

    enabled_option = 'meta_enabled'

    def __init__(self):
        addEvent('renamer.after', self.create)

    def create(self, message = None, group = None):
        if self.isDisabled(): return
        if not group: group = {}

        log.info('Creating %s metadata.', self.getName())

        # Update library to get latest info
        try:
            group['media'] = fireEvent('movie.update_info', group['media'].get('_id'), identifier = getIdentifier(group['media']), extended = True, single = True)
        except:
            log.error('Failed to update movie, before creating metadata: %s', traceback.format_exc())

        root_name = self.getRootName(group)
        meta_name = os.path.basename(root_name)
        root = os.path.dirname(root_name)

        movie_info = group['media'].get('info')

        for file_type in ['nfo', 'thumbnail', 'fanart']:
            try:
                # Get file path
                name = getattr(self, 'get' + file_type.capitalize() + 'Name')(meta_name, root)

                if name and (self.conf('meta_' + file_type) or self.conf('meta_' + file_type) is None):

                    # Get file content
                    content = getattr(self, 'get' + file_type.capitalize())(movie_info = movie_info, data = group)
                    if content:
                        log.debug('Creating %s file: %s', (file_type, name))
                        if os.path.isfile(content):
                            content = sp(content)
                            name = sp(name)

                            shutil.copy2(content, name)
                            shutil.copyfile(content, name)

                            # Try and copy stats seperately
                            try: shutil.copystat(content, name)
                            except: pass
                        else:
                            self.createFile(name, content)
                            group['renamed_files'].append(name)

                        try:
                            os.chmod(sp(name), Env.getPermission('file'))
                        except:
                            log.debug('Failed setting permissions for %s: %s', (name, traceback.format_exc()))

            except:
                log.error('Unable to create %s file: %s', (file_type, traceback.format_exc()))

    def getRootName(self, data = None):
        if not data: data = {}
        return os.path.join(data['destination_dir'], data['filename'])

    def getFanartName(self, name, root):
        return

    def getThumbnailName(self, name, root):
        return

    def getNfoName(self, name, root):
        return

    def getNfo(self, movie_info = None, data = None):
        if not data: data = {}
        if not movie_info: movie_info = {}

    def getThumbnail(self, movie_info = None, data = None, wanted_file_type = 'poster_original'):
        if not data: data = {}
        if not movie_info: movie_info = {}

        # See if it is in current files
        files = data['media'].get('files')
        if files.get('image_' + wanted_file_type):
            if os.path.isfile(files['image_' + wanted_file_type][0]):
                return files['image_' + wanted_file_type][0]

        # Download using existing info
        try:
            images = movie_info['images'][wanted_file_type]
            file_path = fireEvent('file.download', url = images[0], single = True)
            return file_path
        except:
            pass

    def getFanart(self, movie_info = None, data = None):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info = movie_info, data = data, wanted_file_type = 'backdrop_original')
