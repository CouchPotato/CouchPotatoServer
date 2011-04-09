from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.environment import Env
from flask.helpers import json
import base64
import urllib
import urllib2

log = CPLog(__name__)


class Notifo(Notification):

    url = 'https://api.notifo.com/v1/send_notification'

    def __init__(self):
        addEvent('notify', self.notify)
        addEvent('notify.notifo', self.notify)

        addApiView('notify.notifo.test', self.test)

    def conf(self, attr):
        return Env.setting(attr, 'notifo')

    def notify(self, message = '', data = {}):

        if self.isDisabled():
            return False

        try:
            data = urllib.urlencode({
                'msg': toUnicode(message),
            })

            req = urllib2.Request(self.url)
            authHeader = "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('api_key')))[:-1]
            req.add_header("Authorization", authHeader)

            handle = urllib2.urlopen(req, data)
            result = json.load(handle)

            if result['status'] != 'success' or result['response_message'] != 'OK':
                raise Exception

        except Exception, e:
            log.error('Notification failed: %s' % e)
            return False

        log.info('Notifo notification successful.')
        return True
