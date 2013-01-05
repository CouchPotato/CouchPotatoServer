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
            if listener == "test":
                # XBMC JSON-RPC version request
                response = self.request(host, [
                    ('JSONRPC.Version', {})
                ])
            else:
                response = self.request(host, [
                    ('GUI.ShowNotification', {"title":"CouchPotato", "message":message}),
                    ('VideoLibrary.Scan', {}),
                ])

            try:
                for result in response:
                    if (listener != "test" and result['result'] == "OK"):
                        successful += 1
                    elif (listener == "test"):
                        if (type(result['result']['version']).__name__ == 'int'):
                            # fail, only v2 and v4 return an int object
                            # v6 (as of XBMC v12(Frodo)) is required to send notifications
                            xbmc_rpc_version = str(result['result']['version'])
                            log.error("XBMC JSON-RPC Version: %s ; Notifications only supported for v6 [as of XBMC v12(Frodo)]", xbmc_rpc_version)
                            return False

                        elif (type(result['result']['version']).__name__ == 'dict'):
                            # success, v6 returns an array object containing
                            # major, minor and patch number
                            xbmc_rpc_version = str(result['result']['version']['major'])
                            xbmc_rpc_version += "." + str(result['result']['version']['minor'])
                            xbmc_rpc_version += "." + str(result['result']['version']['patch'])
                            log.debug("XBMC JSON-RPC Version: %s", xbmc_rpc_version)
                            # ok, XBMC version is supported, send the text message
                            self.notify(message = message, data = {}, listener = 'test-rpcversion-ok')
                            return True
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

