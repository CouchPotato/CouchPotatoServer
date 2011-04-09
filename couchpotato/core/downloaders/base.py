from couchpotato.core.event import addEvent
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

class Downloader(Plugin):

    def __init__(self):
        addEvent('download', self.download)

    def download(self, data = {}):
        pass

    def conf(self, attr):
        return Env.setting(attr, self.__class__.__name__.lower())

    def isDisabled(self):
        return not self.isEnabled()

    def isEnabled(self):
        return self.conf('enabled', True)
