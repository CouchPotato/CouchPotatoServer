import traceback
import subprocess
import os

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification




log = CPLog(__name__)

autoload = 'Script'

class Script(Notification):

    def __init__(self):
        addApiView(self.testNotifyName(), self.test)

        addEvent('renamer.after', self.runScript)

    def runScript(self, message = None, group = None):
        if self.isDisabled(): return
        if not group: group = {}

        command = [self.conf('path'), group.get('destination_dir')]
        log.info('Executing script command: %s ', command)
        try:
            p = subprocess.Popen(command, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
            out = p.communicate()
            log.info('Result from script: %s', str(out))
            return True
        except OSError as e:
            log.error('Unable to run script: %s', e)

        return False

    def test(self, **kwargs):
        return {
            'success': os.path.isfile(self.conf('path'))
        }

config = [{
    'name': 'script',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'script',
            'label': 'Script',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'path',
                    'description': 'The path to the script to execute.'
                }
            ]
        }
    ]
}]
