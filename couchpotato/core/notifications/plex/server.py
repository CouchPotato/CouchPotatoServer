from datetime import timedelta, datetime
from urlparse import urlparse
import traceback

from couchpotato.core.helpers.variable import cleanHost
from couchpotato import CPLog


try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree

log = CPLog(__name__)


class PlexServer(object):
    def __init__(self, plex):
        self.plex = plex

        self.clients = {}
        self.last_clients_update = None

    def staleClients(self):
        if not self.last_clients_update:
            return True

        return self.last_clients_update + timedelta(minutes=15) < datetime.now()

    def request(self, path, data_type='xml'):
        if not self.plex.conf('media_server'):
            log.warning("Plex media server hostname is required")
            return None

        if path.startswith('/'):
            path = path[1:]

        data = self.plex.urlopen('%s/%s' % (
            self.createHost(self.plex.conf('media_server'), port = 32400),
            path
        ))

        if data_type == 'xml':
            return etree.fromstring(data)
        else:
            return data

    def updateClients(self, client_names):
        log.info('Searching for clients on Plex Media Server')

        self.clients = {}

        result = self.request('clients')
        if not result:
            return

        found_clients = [
            c for c in result.findall('Server')
            if c.get('name') and c.get('name').lower() in client_names
        ]

        # Store client details in cache
        for client in found_clients:
            name = client.get('name').lower()

            self.clients[name] = {
                'name': client.get('name'),
                'found': True,
                'address': client.get('address'),
                'port': client.get('port'),
                'protocol': client.get('protocol', 'xbmchttp')
            }

            client_names.remove(name)

        # Store dummy info for missing clients
        for client_name in client_names:
            self.clients[client_name] = {
                'found': False
            }

        if len(client_names) > 0:
            log.debug('Unable to find clients: %s', ', '.join(client_names))

        self.last_clients_update = datetime.now()

    def refresh(self, section_types=None):
        if not section_types:
            section_types = ['movie']

        sections = self.request('library/sections')

        try:
            for section in sections.findall('Directory'):
                if section.get('type') not in section_types:
                    continue

                self.request('library/sections/%s/refresh' % section.get('key'), 'text')
        except:
            log.error('Plex library update failed for %s, Media Server not running: %s',
                      (self.plex.conf('media_server'), traceback.format_exc(1)))
            return False

        return True

    def createHost(self, host, port = None):

        h = cleanHost(host)
        p = urlparse(h)
        h = h.rstrip('/')

        if port and not p.port:
            h += ':%s' % port

        return h
