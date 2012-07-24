from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toSafeString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env
import os

log = CPLog(__name__)


class Downloader(Plugin):

    type = []

    def __init__(self):
        addEvent('download', self.download)

    def download(self, data = {}):
        pass

    def createNzbName(self, data, movie):
        return '%s%s' % (self.cpTag(movie), toSafeString(data.get('name')))

    def createFileName(self, data, filedata, movie):
        name = os.path.join(self.createNzbName(data, movie))
        if data.get('type') == 'nzb' and 'DOCTYPE nzb' not in filedata and '</nzb>' not in filedata:
            return '%s.%s' % (name, 'rar')
        return '%s.%s' % (name, data.get('type'))

    def cpTag(self, movie):
        if Env.setting('enabled', 'renamer'):
            return 'cp(' + movie['library'].get('identifier') + ').' if movie['library'].get('identifier') else ''

        return ''

    def isCorrectType(self, item_type):
        is_correct = item_type in self.type

        if not is_correct:
            log.debug("Downloader doesn't support this type")

        return is_correct

    def isDisabled(self, manual):
        return not self.isEnabled(manual)

    def isEnabled(self, manual):
        d_manual = self.conf('manual', default = False)
        return super(Downloader, self).isEnabled() and ((d_manual and manual) or (d_manual is False))
