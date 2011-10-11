from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)


class Downloader(Plugin):

    type = []

    def __init__(self):
        addEvent('download', self.download)

    def download(self, data = {}):
        pass

    def createFileExtension(self, data = {}, content):
        pass

    def cpTag(self, movie):
        if Env.setting('enabled', 'renamer'):
            return '.cp(' + movie['library'].get('identifier') + ')' if movie['library'].get('identifier') else ''

        return ''

    def isCorrectType(self, type):
        is_correct = type in self.type

        if not is_correct:
            log.debug("Downloader doesn't support this type")

        return bool
