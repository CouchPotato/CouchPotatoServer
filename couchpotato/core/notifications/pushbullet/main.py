from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import base64
import json

log = CPLog(__name__)


class Pushbullet(Notification):

    url = 'https://api.pushbullet.com/api/%s'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        devices = self.getDevices()
        if devices is None:
            return False

        # Get all the device IDs linked to this user
        if not len(devices):
            response = self.request('devices')
            if not response:
                return False

            devices += [device.get('id') for device in response['devices']]

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

        return successful == len(devices)

    def getDevices(self):
        return splitString(self.conf('devices'))

    def request(self, method, cache = True, **kwargs):
        try:
            base64string = base64.encodestring('%s:' % self.conf('api_key'))[:-1]

            headers = {
                "Authorization": "Basic %s" % base64string
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
