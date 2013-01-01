from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from httplib import HTTPConnection
from urllib import urlencode
import traceback

log = CPLog(__name__)

class Toasty(Notification):

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        data = {
            'title': self.default_title,
            'text': toUnicode(message),
            'sender': toUnicode("CouchPotato"),
            'image': 'https://raw.github.com/RuudBurger/CouchPotatoServer/master/couchpotato/static/images/homescreen.png',
        }

        try:
            http_handler = HTTPConnection("api.supertoasty.com")
            http_handler.request("GET", "/notify/"+self.conf('api_key')+"?"+urlencode(data))
            log.info('Toasty notifications sent.')
            return True
        except:
            log.error('Toasty failed: %s', traceback.format_exc())

        return False
