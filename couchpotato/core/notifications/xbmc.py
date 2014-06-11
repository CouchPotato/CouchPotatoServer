import base64
import json
import socket
import traceback
import urllib

from couchpotato.core.helpers.variable import splitString, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import requests
from requests.packages.urllib3.exceptions import MaxRetryError


log = CPLog(__name__)

autoload = 'XBMC'


class XBMC(Notification):

    listen_to = ['renamer.after', 'movie.snatched']
    use_json_notifications = {}
    http_time_between_calls = 0

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        hosts = splitString(self.conf('host'))

        successful = 0
        max_successful = 0
        for host in hosts:

            if self.use_json_notifications.get(host) is None:
                self.getXBMCJSONversion(host, message = message)

            if self.use_json_notifications.get(host):
                calls = [
                    ('GUI.ShowNotification', None, {'title': self.default_title, 'message': message, 'image': self.getNotificationImage('small')}),
                ]

                if data and data.get('destination_dir') and (not self.conf('only_first') or hosts.index(host) == 0):
                    param = {}
                    if not self.conf('force_full_scan') and (self.conf('remote_dir_scan') or socket.getfqdn('localhost') == socket.getfqdn(host.split(':')[0])):
                        param = {'directory': data['destination_dir']}

                    calls.append(('VideoLibrary.Scan', None, param))

                max_successful += len(calls)
                response = self.request(host, calls)
            else:
                response = self.notifyXBMCnoJSON(host, {'title': self.default_title, 'message': message})

                if data and data.get('destination_dir') and (not self.conf('only_first') or hosts.index(host) == 0):
                    response += self.request(host, [('VideoLibrary.Scan', None, {})])
                    max_successful += 1

                max_successful += 1

            try:
                for result in response:
                    if result.get('result') and result['result'] == 'OK':
                        successful += 1
                    elif result.get('error'):
                        log.error('XBMC error; %s: %s (%s)', (result['id'], result['error']['message'], result['error']['code']))

            except:
                log.error('Failed parsing results: %s', traceback.format_exc())

        return successful == max_successful

    def getXBMCJSONversion(self, host, message = ''):

        success = False

        # XBMC JSON-RPC version request
        response = self.request(host, [
            ('JSONRPC.Version', None, {})
        ])
        for result in response:
            if result.get('result') and type(result['result']['version']).__name__ == 'int':
                # only v2 and v4 return an int object
                # v6 (as of XBMC v12(Frodo)) is required to send notifications
                xbmc_rpc_version = str(result['result']['version'])

                log.debug('XBMC JSON-RPC Version: %s ; Notifications by JSON-RPC only supported for v6 [as of XBMC v12(Frodo)]', xbmc_rpc_version)

                # disable JSON use
                self.use_json_notifications[host] = False

                # send the text message
                resp = self.notifyXBMCnoJSON(host, {'title': self.default_title, 'message': message})
                for r in resp:
                    if r.get('result') and r['result'] == 'OK':
                        log.debug('Message delivered successfully!')
                        success = True
                        break
                    elif r.get('error'):
                        log.error('XBMC error; %s: %s (%s)', (r['id'], r['error']['message'], r['error']['code']))
                        break

            elif result.get('result') and type(result['result']['version']).__name__ == 'dict':
                # XBMC JSON-RPC v6 returns an array object containing
                # major, minor and patch number
                xbmc_rpc_version = str(result['result']['version']['major'])
                xbmc_rpc_version += '.' + str(result['result']['version']['minor'])
                xbmc_rpc_version += '.' + str(result['result']['version']['patch'])

                log.debug('XBMC JSON-RPC Version: %s', xbmc_rpc_version)

                # ok, XBMC version is supported
                self.use_json_notifications[host] = True

                # send the text message
                resp = self.request(host, [('GUI.ShowNotification', None, {'title':self.default_title, 'message':message, 'image': self.getNotificationImage('small')})])
                for r in resp:
                    if r.get('result') and r['result'] == 'OK':
                        log.debug('Message delivered successfully!')
                        success = True
                        break
                    elif r.get('error'):
                        log.error('XBMC error; %s: %s (%s)', (r['id'], r['error']['message'], r['error']['code']))
                        break

            # error getting version info (we do have contact with XBMC though)
            elif result.get('error'):
                log.error('XBMC error; %s: %s (%s)', (result['id'], result['error']['message'], result['error']['code']))

        log.debug('Use JSON notifications: %s ', self.use_json_notifications)

        return success

    def notifyXBMCnoJSON(self, host, data):

        server = 'http://%s/xbmcCmds/' % host

        # Notification(title, message [, timeout , image])
        cmd = "xbmcHttp?command=ExecBuiltIn(Notification(%s,%s,'',%s))" % (urllib.quote(getTitle(data)), urllib.quote(data['message']), urllib.quote(self.getNotificationImage('medium')))
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
            response = self.urlopen(server, headers = headers, timeout = 3, show_error = False)

            if 'OK' in response:
                log.debug('Returned from non-JSON-type request %s: %s', (host, response))
                # manually fake expected response array
                return [{'result': 'OK'}]
            else:
                log.error('Returned from non-JSON-type request %s: %s', (host, response))
                # manually fake expected response array
                return [{'result': 'Error'}]

        except (MaxRetryError, requests.exceptions.Timeout):
            log.info2('Couldn\'t send request to XBMC, assuming it\'s turned off')
            return [{'result': 'Error'}]
        except:
            log.error('Failed sending non-JSON-type request to XBMC: %s', traceback.format_exc())
            return [{'result': 'Error'}]

    def request(self, host, do_requests):
        server = 'http://%s/jsonrpc' % host

        data = []
        for req in do_requests:
            method, id, kwargs = req

            data.append({
                'method': method,
                'params': kwargs,
                'jsonrpc': '2.0',
                'id': id if id else method,
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
            response = self.getJsonData(server, headers = headers, data = data, timeout = 3, show_error = False)
            log.debug('Returned from request %s: %s', (host, response))

            return response
        except (MaxRetryError, requests.exceptions.Timeout):
            log.info2('Couldn\'t send request to XBMC, assuming it\'s turned off')
            return []
        except:
            log.error('Failed sending request to XBMC: %s', traceback.format_exc())
            return []


config = [{
    'name': 'xbmc',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'xbmc',
            'label': 'XBMC',
            'description': 'v11 (Eden), v12 (Frodo), v13 (Gotham)',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'host',
                    'default': 'localhost:8080',
                },
                {
                    'name': 'username',
                    'default': 'xbmc',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
                },
                {
                    'name': 'only_first',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Only update the first host when movie snatched, useful for synced XBMC',
                },
                {
                    'name': 'remote_dir_scan',
                    'label': 'Remote Folder Scan',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': ('Only scan new movie folder at remote XBMC servers.', 'Useful if the XBMC path is different from the path CPS uses.'),
                },
                {
                    'name': 'force_full_scan',
                    'label': 'Always do a full scan',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': ('Do a full scan instead of only the new movie.', 'Useful if the XBMC path is different from the path CPS uses.'),
                },
                {
                    'name': 'on_snatch',
                    'default': False,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
