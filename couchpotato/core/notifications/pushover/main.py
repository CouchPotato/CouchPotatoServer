from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from httplib import HTTPSConnection

log = CPLog(__name__)


class Pushover(Notification):

    app_token = 'YkxHMYDZp285L265L3IwH3LmzkTaCy'

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        http_handler = HTTPSConnection("api.pushover.net:443")

        api_data = {
            'user': self.conf('user_key'),
            'token': self.app_token,
            'message': toUnicode(message),
            'priority': self.conf('priority'),
        }

        if data and data.get('library'):
            api_data.update({
                'url': toUnicode('http://www.imdb.com/title/%s/' % data['library']['identifier']),
                'url_title': toUnicode('%s on IMDb' % getTitle(data['library'])),
            })

        http_handler.request('POST',
                             "/1/messages.json",
                             headers = {'Content-type': 'application/x-www-form-urlencoded'},
                             body = tryUrlencode(api_data)
        )

        response = http_handler.getresponse()
        request_status = response.status

        if request_status == 200:
            log.info('Pushover notifications sent.')
            return True
        elif request_status == 401:
            log.error('Pushover auth failed: %s', response.reason)
            return False
        else:
            log.error('Pushover notification failed.')
            return False
