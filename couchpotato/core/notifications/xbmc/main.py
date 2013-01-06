from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from flask.helpers import json
import base64
import traceback
import urllib

log = CPLog(__name__)


class XBMC(Notification):

    listen_to = ['renamer.after']
    firstRun = True
    useJSONnotifications = True

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        hosts = splitString(self.conf('host'))
        if self.firstRun or listener == "test" : return self.getXBMCJSONversion(hosts, message=message )

        successful = 0
        for host in hosts:
            if self.useJSONnotifications:
                response = self.request(host, [
                    ('GUI.ShowNotification', {"title":self.default_title, "message":message}),
                    ('VideoLibrary.Scan', {}),
                ])
            else:
                response = self.notifyXBMCnoJSON(host, {'title':self.default_title,'message':message})
                response += self.request(host, [('VideoLibrary.Scan', {})])

            try:
                for result in response:
                    if (result.get('result') and result['result'] == "OK"):
                        successful += 1
                    elif (result.get('error')):
                        log.error("XBMC error; %s: %s (%s)", (result['id'], result['error']['message'], result['error']['code']))

            except:
                log.error('Failed parsing results: %s', traceback.format_exc())

        return successful == len(hosts) * 2

    # TODO: implement multiple hosts support, for now the last host of the 'hosts' array
    # sets 'useJSONnotifications'
    def getXBMCJSONversion(self, hosts, message=''):

        success = 0
        for host in hosts:
            # XBMC JSON-RPC version request
            response = self.request(host, [
                ('JSONRPC.Version', {})
                ])
            for result in response:
                if (result.get('result') and type(result['result']['version']).__name__ == 'int'):
                    # only v2 and v4 return an int object
                    # v6 (as of XBMC v12(Frodo)) is required to send notifications
                    xbmc_rpc_version = str(result['result']['version'])

                    log.debug("XBMC JSON-RPC Version: %s ; Notifications by JSON-RPC only supported for v6 [as of XBMC v12(Frodo)]", xbmc_rpc_version)

                    # disable JSON use
                    self.useJSONnotifications = False

                    # send the text message
                    resp = self.notifyXBMCnoJSON(host, {'title':self.default_title,'message':message})
                    for result in resp:
                        if (result.get('result') and result['result'] == "OK"):
                            log.debug("Message delivered successfully!")
                            success = True
                            break
                        elif (result.get('error')):
                            log.error("XBMC error; %s: %s (%s)", (result['id'], result['error']['message'], result['error']['code']))
                            break

                elif (result.get('result') and type(result['result']['version']).__name__ == 'dict'):
                    # XBMC JSON-RPC v6 returns an array object containing
                    # major, minor and patch number
                    xbmc_rpc_version = str(result['result']['version']['major'])
                    xbmc_rpc_version += "." + str(result['result']['version']['minor'])
                    xbmc_rpc_version += "." + str(result['result']['version']['patch'])

                    log.debug("XBMC JSON-RPC Version: %s", xbmc_rpc_version)

                    # ok, XBMC version is supported
                    self.useJSONnotifications = True

                    # send the text message
                    resp = self.request(host, [('GUI.ShowNotification', {"title":self.default_title, "message":message})])
                    for result in resp:
                        if (result.get('result') and result['result'] == "OK"):
                            log.debug("Message delivered successfully!")
                            success = True
                            break
                        elif (result.get('error')):
                            log.error("XBMC error; %s: %s (%s)", (result['id'], result['error']['message'], result['error']['code']))
                            break

                # error getting version info (we do have contact with XBMC though)
                elif (result.get('error')):
                    log.error("XBMC error; %s: %s (%s)", (result['id'], result['error']['message'], result['error']['code']))

        # set boolean so we only run this once after boot
        # in func notify() ignored for 'test' messages
        self.firstRun = False

        log.debug("use JSON notifications: %s ", self.useJSONnotifications)

        return success

    def notifyXBMCnoJSON(self, host, data):

        server = 'http://%s/xbmcCmds/' % host

        # title, message [, timeout , image #can be added!]
        cmd = 'xbmcHttp?command=ExecBuiltIn(Notification("%s","%s"))' % (urllib.quote(data['title']), urllib.quote(data['message']))
        server += cmd

        # I have no idea what to set to, just tried text/plain and seems to be working :)
        headers = {
            'Content-Type': 'text/plain',
        }

        # authentication support
        if self.conf('password'):
            base64string = base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password'))).replace('\n', '')
            headers['Authorization'] = 'Basic %s' % base64string

        try:
            log.debug('Sending non-JSON-type request to %s: %s', (host, data))

            # response wil either be 'OK':
            # <html>
            # <li>OK
            # </html>
            #
            # or 'Error':
            # <html>
            # <li>Error:<message>
            # </html>
            #
            response = self.urlopen(server, headers = headers)

            if "OK" in response:
                log.debug('Returned from non-JSON-type request %s: %s', (host, response))
                # manually fake expected response array
                return [{"result": "OK"}]
            else:
                log.error('Returned from non-JSON-type request %s: %s', (host, response))
                # manually fake expected response array
                return [{"result": "Error"}]

        except:
            log.error('Failed sending non-JSON-type request to XBMC: %s', traceback.format_exc())
            return [{"result": "Error"}]

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

