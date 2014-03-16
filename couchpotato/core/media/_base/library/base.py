from couchpotato.core.event import addEvent
from couchpotato.core.plugins.base import Plugin


class LibraryBase(Plugin):

    _type = None

    def initType(self):
        addEvent('library.types', self.getType)

    def getType(self):
        return self._type
