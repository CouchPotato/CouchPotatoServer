from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
import time

log = CPLog(__name__)


class Automation(Plugin):

    enabled_option = 'automation_enabled'

    interval = 86400
    last_checked = 0

    def __init__(self):
        addEvent('automation.get_movies', self._getMovies)

    def _getMovies(self):

        if not self.canCheck():
            log.debug('Just checked, skipping %s' % self.getName())
            return []

        self.last_checked = time.time()

        return self.getIMDBids()


    def getIMDBids(self):
        return []

    def canCheck(self):
        return time.time() > self.last_checked + self.interval
