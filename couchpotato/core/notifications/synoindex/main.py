from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import os
import subprocess

log = CPLog(__name__)


class Synoindex(Notification):

    index_path = '/usr/syno/bin/synoindex'

    def __init__(self):
        super(Synoindex, self).__init__()
        addEvent('renamer.after', self.addToLibrary)

    def addToLibrary(self, message = None, group = None):
        if self.isDisabled(): return
        if not group: group = {}

        command = [self.index_path, '-A', group.get('destination_dir')]
        log.info('Executing synoindex command: %s ', command)
        try:
            p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            out = p.communicate()
            log.info('Result from synoindex: %s', str(out))
            return True
        except OSError, e:
            log.error('Unable to run synoindex: %s', e)

        return False

    def test(self, **kwargs):
        return {
            'success': os.path.isfile(self.index_path)
        }
