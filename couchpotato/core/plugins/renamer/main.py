from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Renamer(Plugin):

    def __init__(self):
        pass

        addEvent('renamer.scan', self.scan)
        addEvent('app.load', self.scan)

        fireEvent('schedule.interval', 'renamer.scan', self.scan, minutes = self.conf('run_every'))

    def scan(self):
        print 'scan'
