from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import traceback

log = CPLog(__name__)

class Toasty(Notification):

    urls = {
        'api': 'http://api.supertoasty.com/notify/%s?%s'
    }

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        data = {
            'title': self.default_title,
            'text': toUnicode(message),
            'sender': toUnicode("CouchPotato"),
            'image': 'https://raw.github.com/RuudBurger/CouchPotatoServer/master/couchpotato/static/images/homescreen.png',
        }

        try:
            self.urlopen(self.urls['api'] % (self.conf('api_key'), tryUrlencode(data)), show_error = False)
            return True
        except:
            log.error('Toasty failed: %s', traceback.format_exc())

        return False
