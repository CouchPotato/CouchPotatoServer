from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import os.path
import shutil
import traceback

log = CPLog(__name__)


class MetaDataBase(Plugin):

    enabled_option = 'meta_enabled'

    def __init__(self):
        addEvent('renamer.after', self.create)

    def create(self, release):
        if self.isDisabled(): return

        log.info('Creating %s metadata.' % self.getName())

        root = self.getRootName(release)

        for type in ['nfo', 'thumbnail', 'fanart']:
            try:
                # Get file path
                name = getattr(self, 'get' + type.capitalize() + 'Name')(root)

                if name and self.conf('meta_' + type):

                    # Get file content
                    content = getattr(self, 'get' + type.capitalize())(release)
                    if content:
                        log.debug('Creating %s file: %s' % (type, name))
                        if os.path.isfile(content):
                            shutil.copy2(content, name)
                        else:
                            self.createFile(name, content)

            except Exception, e:
                log.error('Unable to create %s file: %s' % (type, traceback.format_exc()))

    def getRootName(self, data):
        return

    def getFanartName(self, root):
        return

    def getThumbnailName(self, root):
        return

    def getNfoName(self, root):
        return

    def getNfo(self, data):
        return

    def getThumbnail(self, data, file_type = 'poster_original'):
        file_types = fireEvent('file.types', single = True)
        for type in file_types:
            if type.get('identifier') == file_type:
                break

        for file in data['library'].get('files'):
            if file.get('type_id') is type.get('id'):
                return file.get('path')

    def getFanart(self, data):
        return self.getThumbnail(data, file_type = 'backdrop_original')
