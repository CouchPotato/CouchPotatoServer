from couchpotato.core.event import addEvent
from couchpotato.core.plugins.base import Plugin


class Downloader(Plugin):

    def __init__(self):
        addEvent('download', self.download)

    def download(self, data = {}):
        pass

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf('enabled', True)
