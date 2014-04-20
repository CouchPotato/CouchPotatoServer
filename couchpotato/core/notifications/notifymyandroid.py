from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import pynma
import six

log = CPLog(__name__)

autoload = 'NotifyMyAndroid'


class NotifyMyAndroid(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        nma = pynma.PyNMA()
        keys = splitString(self.conf('api_key'))
        nma.addkey(keys)
        nma.developerkey(self.conf('dev_key'))

        response = nma.push(
            application = self.default_title,
            event = message.split(' ')[0],
            description = message,
            priority = self.conf('priority'),
            batch_mode = len(keys) > 1
        )

        successful = 0
        for key in keys:
            if not response[str(key)]['code'] == six.u('200'):
                log.error('Could not send notification to NotifyMyAndroid (%s). %s', (key, response[key]['message']))
            else:
                successful += 1

        return successful == len(keys)


config = [{
    'name': 'notifymyandroid',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'notifymyandroid',
            'label': 'Notify My Android',
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
