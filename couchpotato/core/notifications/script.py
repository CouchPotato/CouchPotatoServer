import traceback
import subprocess

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Script'

class Script(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        script_data = {
            'message': toUnicode(message)
        }

        if getIdentifier(data):
            script_data.update({
                'imdb_id': getIdentifier(data)
            })

        try:
            subprocess.call([self.conf('path'), message])
            return True
        except:
            log.error('Script notification failed: %s', traceback.format_exc())

        return False


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
