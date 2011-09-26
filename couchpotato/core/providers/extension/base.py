from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class ExtensionBase(Plugin):

    version = 1

    includes = []
    excludes = []

    def __init__(self):
        addEvent('extension.add_via_url', self.addViaUrl)
        addEvent('extension.get_includes', self.getInclude)
        addEvent('extension.get_excludes', self.getExclude)

        addEvent('extension.get_version', self.getVersion)

    def addViaUrl(self):
        pass

    def getInclude(self):
        return self.includes

    def getExclude(self):
        return self.excludes

    def getVersion(self):
        return self.version
