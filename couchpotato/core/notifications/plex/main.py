from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from datetime import datetime
from urlparse import urlparse
from xml.dom import minidom
import json
import requests
import traceback

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = CPLog(__name__)


class Plex(Notification):

    client_update_time = 5 * 60
    http_time_between_calls = 0

    def __init__(self):
        super(Plex, self).__init__()

        self.clients = {}
        self.clients_updated = None

        addEvent('renamer.after', self.addToLibrary)

    def updateClients(self, force = False):
        if not self.conf('media_server'):
            log.warning("Plex media server hostname is required")
            return

        since_update = ((datetime.now() - self.clients_updated).total_seconds())\
            if self.clients_updated is not None else None

        if force or self.clients_updated is None or since_update > self.client_update_time:
            self.clients = {}

            data = self.urlopen('%s/clients' % self.createHost(self.conf('media_server'), port = 32400))
            client_result = etree.fromstring(data)

            clients = [x.strip().lower() for x in self.conf('clients').split(',')]

            for server in client_result.findall('Server'):
                if server.get('name').lower() in clients:
                    clients.remove(server.get('name').lower())
                    protocol = server.get('protocol', 'xbmchttp')

                    if protocol in ['plex', 'xbmcjson', 'xbmchttp']:
                        self.clients[server.get('name')] = {
                            'name': server.get('name'),
                            'address': server.get('address'),
                            'port': server.get('port'),
                            'protocol': protocol
                        }

            if len(clients) > 0:
                log.info2('Unable to find plex clients: %s', ', '.join(clients))

            log.info2('Found hosts: %s', ', '.join(self.clients.keys()))

            self.clients_updated = datetime.now()


    def addToLibrary(self, message = None, group = {}):
        if self.isDisabled(): return

        log.info('Sending notification to Plex')

        source_type = ['movie']
        base_url = '%s/library/sections' % self.createHost(self.conf('media_server'), port = 32400)
        refresh_url = '%s/%%s/refresh' % base_url

        try:
            sections_xml = self.urlopen(base_url)
            xml_sections = minidom.parseString(sections_xml)
            sections = xml_sections.getElementsByTagName('Directory')

            for s in sections:
                if s.getAttribute('type') in source_type:
                    url = refresh_url % s.getAttribute('key')
                    x = self.urlopen(url)

        except:
            log.error('Plex library update failed for %s, Media Server not running: %s',
                      (self.conf('media_server'), traceback.format_exc(1)))
            return False

        return True

    def sendHTTP(self, command, client):
        url = 'http://%s:%s/xbmcCmds/xbmcHttp/?%s' % (
            client['address'],
            client['port'],
            tryUrlencode(command)
        )

        headers = {}

        try:
            self.urlopen(url, headers = headers, timeout = 3, show_error = False)
        except Exception, err:
            log.error("Couldn't sent command to Plex: %s", err)
            return False

        return True

    def notifyHTTP(self, message = '', data = {}, listener = None):
        total = 0
        successful = 0

        data = {
            'command': 'ExecBuiltIn',
            'parameter': 'Notification(CouchPotato, %s)' % message
        }

        for name, client in self.clients.items():
            if client['protocol'] == 'xbmchttp':
                total += 1
                if self.sendHTTP(data, client):
                    successful += 1

        return successful == total

    def sendJSON(self, method, params, client):
        log.debug('sendJSON("%s", %s, %s)', (method, params, client))
        url = 'http://%s:%s/jsonrpc' % (
            client['address'],
            client['port']
        )

        headers = {
            'Content-Type': 'application/json'
        }

        request = {
            'id':1,
            'jsonrpc': '2.0',
            'method': method,
            'params': params
        }

        try:
            requests.post(url, headers = headers, timeout = 3, data = json.dumps(request))
        except Exception, err:
            log.error("Couldn't sent command to Plex: %s", err)
            return False

        return True

    def notifyJSON(self, message = '', data = {}, listener = None):
        total = 0
        successful = 0

        params = {
            'title': 'CouchPotato',
            'message': message
        }

        for name, client in self.clients.items():
            if client['protocol'] in ['xbmcjson', 'plex']:
                total += 1
                if self.sendJSON('GUI.ShowNotification', params, client):
                    successful += 1

        return successful == total

    def notify(self, message = '', data = {}, listener = None, force = False):
        self.updateClients(force)

        http_result = self.notifyHTTP(message, data, listener)
        json_result = self.notifyJSON(message, data, listener)

        return http_result and json_result

    def test(self, **kwargs):

        test_type = self.testNotifyName()

        log.info('Sending test to %s', test_type)

        success = self.notify(
            message = self.test_message,
            data = {},
            listener = 'test',
            force = True
        )
        success2 = self.addToLibrary()

        return {
            'success': success or success2
        }

    def createHost(self, host, port = None):

        h = cleanHost(host)
        p = urlparse(h)
        h = h.rstrip('/')
        if port and not p.port:
            h += ':%s' % port

        return h
