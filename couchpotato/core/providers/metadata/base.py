from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class MetaDataBase(Plugin):

    def __init__(self):
        addEvent('metadata.create', self.create)

    def create(self):
        print 'create metadata %s' % __name__

    def getFanartName(self):
        return

    def getThumbnailName(self):
        return

    def getNfoName(self):
        return

    def getNfo(self):
        return
