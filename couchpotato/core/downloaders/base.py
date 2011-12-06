from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
from couchpotato.core.helpers.encoding import toSafeString
import os

log = CPLog(__name__)


class Downloader(Plugin):

    type = []

    def __init__(self):
        addEvent('download', self.download)

    def download(self, data = {}):
        pass

    def createFileName(self, data, filename, movie):
        name = os.path.join('%s%s' % (toSafeString(data.get('name')), self.cpTag(movie)))
        if data.get('type') == 'nzb' and "DOCTYPE nzb" not in filename:
            return '%s.%s' % (name, 'rar')
        return '%s.%s' % (name, data.get('type'))

    def cpTag(self, movie):
        if Env.setting('enabled', 'renamer'):
            return '.cp(' + movie['library'].get('identifier') + ')' if movie['library'].get('identifier') else ''

        return ''

    def isCorrectType(self, type):
        is_correct = type in self.type

        if not is_correct:
            log.debug("Downloader doesn't support this type")

        return bool
