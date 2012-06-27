from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.providers.automation.trakt import Trakt
import base64
from hashlib import sha1
import json
import urllib2

log = CPLog(__name__)


class Trakt(Notification):

    listen_to = ['movie.downloaded']
    api_url = 'http://api.trakt.tv/movie/library/%s'

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        trakt = Trakt()

        api_key = trakt.conf('automation_api_key')
        username = trakt.conf('automation_username')
        password = trakt.conf('automation_password')

        request = {}
        request['username'] = username
        request['password'] = password
        request['movies'] = {'imdb_id' : data['imdb'], 'title' : data['title'], 'year' : data['year']}
        json_request = json.dumps(request)

        url = self.api_url % api_key

        try:
           urllib2.urlopen(url = url, data = json_request)
           log.info("Added %s (%s) to Trakt library" % (data['title'], data['year']))

        except:
            log.error("API call failed")
            return False

        return True