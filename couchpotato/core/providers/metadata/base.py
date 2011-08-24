from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class MetaDataBase(Plugin):

    enabled_option = 'meta_enabled'

    def __init__(self):
        addEvent('metadata.create', self.create)

    def create(self, release):
        if self.isDisabled(): return

        log.info('Creating %s metadata.' % self.getName())

        root = self.getRootName()

        for type in ['nfo', 'thumbnail', 'fanart']:
            try:
                # Get file path
                name = getattr(self, 'get' + type.capitalize() + 'Name')(root)

                if name and self.conf('meta_' + type):

                    # Get file content
                    content = getattr(self, 'get' + type.capitalize())(release)
                    if content:
                        log.debug('Creating %s file: %s' % (type, name))
                        self.createFile(name, content)

            except Exception, e:
                log.error('Unable to create %s file: %s' % (type, e))

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

    def getThumbnail(self, data):
        return

    def getFanart(self, data):
        return
