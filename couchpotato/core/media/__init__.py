from couchpotato.core.event import addEvent
from couchpotato.core.plugins.base import Plugin


class MediaBase(Plugin):

    _type = None

    def initType(self):
        addEvent('media.types', self.getType)

    def getType(self):
        return self._type
