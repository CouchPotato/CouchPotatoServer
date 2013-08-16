from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class MediaBase(Plugin):

    identifier = None

    def __init__(self):

        addEvent('media.types', self.getType)

    def getType(self):
        return self.identifier
