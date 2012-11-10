from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from flask.helpers import json
import base64
import traceback

log = CPLog(__name__)


class XBMC(Notification):

    listen_to = ['renamer.after']

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        hosts = splitString(self.conf('host'))
        successful = 0
        for host in hosts:
            response = self.request(host, [
                ('GUI.ShowNotification', {"title":"CouchPotato", "message":message}),
                ('VideoLibrary.Scan', {}),
            ])

            try:
                for result in response:
                    if result['result'] == "OK":
                        successful += 1
            except:
                log.error('Failed parsing results: %s', traceback.format_exc())

        return successful == len(hosts) * 2

    def request(self, host, requests):
        server = 'http://%s/jsonrpc' % host

        data = []
        for req in requests:
            method, kwargs = req
            data.append({
                'method': method,
                'params': kwargs,
                'jsonrpc': '2.0',
                'id': method,
            })
        data = json.dumps(data)

        headers = {
            'Content-Type': 'application/json',
        }

        if self.conf('password'):
            base64string = base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password'))).replace('\n', '')
            headers['Authorization'] = 'Basic %s' % base64string

        try:
            log.debug('Sending request to %s: %s', (host, data))
            rdata = self.urlopen(server, headers = headers, params = data, multipart = True)
            response = json.loads(rdata)
            log.debug('Returned from request %s: %s', (host, response))

            return response
        except:
            log.error('Failed sending request to XBMC: %s', traceback.format_exc())
            return []

