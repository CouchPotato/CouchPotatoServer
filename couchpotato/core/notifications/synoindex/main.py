from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import subprocess

log = CPLog(__name__)


class Synoindex(Notification):

    def __init__(self):
        addEvent('renamer.after', self.addToLibrary)

    def addToLibrary(self, group = {}):
        if self.isDisabled(): return

        command = ['/usr/syno/bin/synoindex', '-A', group.get('destination_dir')]
        log.info(u'Executing synoindex command: %s ', command)
        try:
            p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            out = p.communicate()
            log.info('Result from synoindex: %s', str(out))
            return True
        except OSError, e:
            log.error('Unable to run synoindex: %s', e)
            return False

        return True
