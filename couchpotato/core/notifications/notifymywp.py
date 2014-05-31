from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from pynmwp import PyNMWP
import six

log = CPLog(__name__)

autoload = 'NotifyMyWP'


class NotifyMyWP(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        keys = splitString(self.conf('api_key'))
        p = PyNMWP(keys, self.conf('dev_key'))

        response = p.push(application = self.default_title, event = message, description = message, priority = self.conf('priority'), batch_mode = len(keys) > 1)

        for key in keys:
            if not response[key]['Code'] == six.u('200'):
                log.error('Could not send notification to NotifyMyWindowsPhone (%s). %s', (key, response[key]['message']))
                return False

        return response


config = [{
    'name': 'notifymywp',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'notifymywp',
            'label': 'Windows Phone',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'description': 'Multiple keys seperated by a comma. Maximum of 5.'
                },
                {
                    'name': 'dev_key',
                    'advanced': True,
                },
                {
                    'name': 'priority',
                    'default': 0,
                    'type': 'dropdown',
                    'values': [('Very Low', -2), ('Moderate', -1), ('Normal', 0), ('High', 1), ('Emergency', 2)],
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
