import base64
import json

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Pushbullet'


class Pushbullet(Notification):

    url = 'https://api.pushbullet.com/v2/%s'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        # Get all the device IDs linked to this user
        devices = self.getDevices() or []
        successful = 0
        for device in devices:
            response = self.request(
                'pushes',
                cache = False,
                device_iden = device,
                type = 'note',
                title = self.default_title,
                body = toUnicode(message)
            )

            if response:
                successful += 1
            else:
                log.error('Unable to push notification to Pushbullet device with ID %s' % device)

        for channel in self.getChannels():
            response = self.request(
                'pushes',
                cache = False,
                channel_tag = channel,
                type = 'note',
                title = self.default_title,
                body = toUnicode(message)
            )

        return successful == len(devices)

    def getDevices(self):
        return splitString(self.conf('devices'))

    def getChannels(self):
        return splitString(self.conf('channels'))

    def request(self, method, cache = True, **kwargs):
        try:
            base64string = base64.encodestring('%s:' % self.conf('api_key'))[:-1]

            headers = {
                'Authorization': 'Basic %s' % base64string
            }

            if cache:
                return self.getJsonData(self.url % method, headers = headers, data = kwargs)
            else:
                data = self.urlopen(self.url % method, headers = headers, data = kwargs)
                return json.loads(data)

        except Exception as ex:
            log.error('Pushbullet request failed')
            log.debug(ex)

        return None


config = [{
    'name': 'pushbullet',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'pushbullet',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'api_key',
                    'label': 'Access Token',
                    'description': 'Can be found on <a href="https://www.pushbullet.com/account" target="_blank">Account Settings</a>',
                },
                {
                    'name': 'devices',
                    'default': '',
                    'advanced': True,
                    'description': 'IDs of devices to send notifications to, empty = all devices'
                },
                {
                    'name': 'channels',
                    'default': '',
                    'advanced': True,
                    'description': 'IDs of channels to send notifications to, empty = no channels'
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
