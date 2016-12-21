import json
import urllib, urllib2

from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification


log = CPLog(__name__)

autoload = 'Emby'


class Emby(Notification):

    def notify(self, message = '', data = None, listener = None):
        host = self.conf('host')
        apikey = self.conf('apikey')

        host = cleanHost(host)
        url = '%semby/Library/Movies/Updated' % (host)
        values = {}
        data = urllib.urlencode(values)

        try:
            req = urllib2.Request(url, data)
            req.add_header('X-MediaBrowser-Token', apikey)

            response = urllib2.urlopen(req)
            result = response.read()
            response.close()
            return True

        except (urllib2.URLError, IOError), e:
            return False

    def test(self, **kwargs):
        host = self.conf('host')
        apikey = self.conf('apikey')
        message = self.test_message

        host = cleanHost(host)
        url = '%semby/Notifications/Admin' % (host)
        values = {'Name': 'CouchPotato', 'Description': message, 'ImageUrl': 'https://raw.githubusercontent.com/CouchPotato/CouchPotatoServer/master/couchpotato/static/images/notify.couch.small.png'}
        data = json.dumps(values)

        try:
            req = urllib2.Request(url, data)
            req.add_header('X-MediaBrowser-Token', apikey)
            req.add_header('Content-Type', 'application/json')

            response = urllib2.urlopen(req)
            result = response.read()
            response.close()
            return {
                'success': True
            }

        except (urllib2.URLError, IOError), e:
            return False


config = [{
    'name': 'emby',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'emby',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8096',
                    'description': 'IP:Port, default localhost:8096'
                },
                {
                    'name': 'apikey',
                    'label': 'API Key',
                    'default': '',
                },
            ],
        }
    ],
}]
