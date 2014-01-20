import json
from couchpotato import CPLog
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import tryUrlencode
import requests

log = CPLog(__name__)


class PlexClientProtocol(object):
    def __init__(self, plex):
        self.plex = plex

        addEvent('notify.plex.notifyClient', self.notify)

    def notify(self, client, message):
        raise NotImplementedError()


class PlexClientHTTP(PlexClientProtocol):
    def request(self, command, client):
        url = 'http://%s:%s/xbmcCmds/xbmcHttp/?%s' % (
            client['address'],
            client['port'],
            tryUrlencode(command)
        )

        headers = {}

        try:
            self.plex.urlopen(url, headers = headers, timeout = 3, show_error = False)
        except Exception as err:
            log.error("Couldn't sent command to Plex: %s", err)
            return False

        return True

    def notify(self, client, message):
        if client.get('protocol') != 'xbmchttp':
            return None

        data = {
            'command': 'ExecBuiltIn',
            'parameter': 'Notification(CouchPotato, %s)' % message
        }

        return self.request(data, client)


class PlexClientJSON(PlexClientProtocol):
    def request(self, method, params, client):
        log.debug('sendJSON("%s", %s, %s)', (method, params, client))
        url = 'http://%s:%s/jsonrpc' % (
            client['address'],
            client['port']
        )

        headers = {
            'Content-Type': 'application/json'
        }

        request = {
            'id': 1,
            'jsonrpc': '2.0',
            'method': method,
            'params': params
        }

        try:
            requests.post(url, headers = headers, timeout = 3, data = json.dumps(request))
        except Exception as err:
            log.error("Couldn't sent command to Plex: %s", err)
            return False

        return True

    def notify(self, client, message):
        if client.get('protocol') not in ['xbmcjson', 'plex']:
            return None

        params = {
            'title': 'CouchPotato',
            'message': message
        }
        return self.request('GUI.ShowNotification', params, client)
