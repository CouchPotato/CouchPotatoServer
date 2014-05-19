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
        
        for file_type in ['nfo']:
            try:
                self._createType(meta_name, root, movie_info, group, file_type, 0)
            except:
                log.error('Unable to create %s file: %s', ('nfo', traceback.format_exc()))

        for file_type in ['thumbnail', 'fanart', 'banner', 'discart', 'logo', 'clearart', 'landscape', 'extrathumbs', 'extrafanart']:
            try:
                if file_type == 'thumbnail':
                    numImages = len(movie_info['images']['poster_original'])
                elif file_type == 'fanart':
                    numImages = len(movie_info['images']['backdrop_original'])
                else:
                    numImages = len(movie_info['images'][file_type])

                for i in range(numImages):
                    self._createType(meta_name, root, movie_info, group, file_type, i)
            except:
                log.error('Unable to create %s file: %s', (file_type, traceback.format_exc()))

    def _createType(self, meta_name, root, movie_info, group, file_type, i):# Get file path
        name = getattr(self, 'get' + file_type.capitalize() + 'Name')(meta_name, root, i)

        if name and (self.conf('meta_' + file_type) or self.conf('meta_' + file_type) is None):

            # Get file content
            content = getattr(self, 'get' + file_type.capitalize())(movie_info=movie_info, data=group, i=i)
            if content:
                log.debug('Creating %s file: %s', (file_type, name))
                if os.path.isfile(content):
                    content = sp(content)
                    name = sp(name)

                    if not os.path.exists(os.path.dirname(name)):
                        os.makedirs(os.path.dirname(name))

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

    def getRootName(self, data = None):
        if not data: data = {}
        return os.path.join(data['destination_dir'], data['filename'])

    def getFanartName(self, name, root, i):
        return

    def getThumbnailName(self, name, root, i):
        return

    def getBannerName(self, name, root, i):
        return

    def getClearartName(self, name, root, i):
        return

    def getLogoName(self, name, root, i):
        return

    def getDiscartName(self, name, root, i):
        return

    def getLandscapeName(self, name, root, i):
        return
    
    def getExtrathumbsName(self, name, root, i):
        return

    def getExtrafanartName(self, name, root, i):
        return

    def getNfoName(self, name, root, i):
        return

    def getNfo(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}

    def getThumbnail(self, movie_info = None, data = None, wanted_file_type = 'poster_original', i = 0):
        if not data: data = {}
        if not movie_info: movie_info = {}

        # See if it is in current files
        files = data['media'].get('files')
        if files.get('image_' + wanted_file_type):
            if os.path.isfile(files['image_' + wanted_file_type][i]):
                return files['image_' + wanted_file_type][i]

        # Download using existing info
        try:
            images = movie_info['images'][wanted_file_type]
            file_path = fireEvent('file.download', url = images[i], single = True)
            return file_path
        except:
            pass

    def getFanart(self, movie_info = None, data = None, i = 0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='backdrop_original', i=i)

    def getBanner(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='banner', i=i)

    def getClearart(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='clearart', i=i)

    def getLogo(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='logo', i=i)

    def getDiscart(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='discart', i=i)

    def getLandscape(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='landscape', i=i)

    def getExtrathumbs(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='extrathumbs', i=i)

    def getExtrafanart(self, movie_info=None, data=None, i=0):
        if not data: data = {}
        if not movie_info: movie_info = {}
        return self.getThumbnail(movie_info=movie_info, data=data, wanted_file_type='extrafanart', i=i)
