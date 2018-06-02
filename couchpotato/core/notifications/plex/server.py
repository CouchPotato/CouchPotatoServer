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

        #Maintain support for older Plex installations without myPlex
        if not self.plex.conf('auth_token') and not self.plex.conf('username') and not self.plex.conf('password'):
            data = self.plex.urlopen('%s/%s' % (
                self.createHost(self.plex.conf('media_server'), port = self.plex.conf('media_server_port'), use_https = self.plex.conf('use_https')),
                path
            ))
        else:
            #Fetch X-Plex-Token if it doesn't exist but a username/password do
            if not self.plex.conf('auth_token') and (self.plex.conf('username') and self.plex.conf('password')):
                import urllib2, base64
                log.info("Fetching a new X-Plex-Token from plex.tv")
                username = self.plex.conf('username')
                password = self.plex.conf('password')
                req = urllib2.Request("https://plex.tv/users/sign_in.xml", data="")
                authheader = "Basic %s" % base64.encodestring('%s:%s' % (username, password))[:-1]
                req.add_header("Authorization", authheader)
                req.add_header("X-Plex-Device-Name", "CouchPotato")
                req.add_header("X-Plex-Product", "CouchPotato Notifier")
                req.add_header("X-Plex-Client-Identifier", "b3a6b24dcab2224bdb101fc6aa08ea5e2f3147d6")
                req.add_header("X-Plex-Version", "1.0")

                try:
                    response = urllib2.urlopen(req)
                except urllib2.URLError, e:
                    log.info('Error fetching token from plex.tv: %s', traceback.format_exc())

                try:
                    auth_tree = etree.parse(response)
                    token = auth_tree.findall(".//authentication-token")[0].text
                    self.plex.conf('auth_token', token)

                except (ValueError, IndexError) as e:
                    log.info("Error parsing plex.tv response: " + ex(e))

            #Add X-Plex-Token header for myPlex support workaround
            data = self.plex.urlopen('%s/%s?X-Plex-Token=%s' % (
                self.createHost(self.plex.conf('media_server'), port = self.plex.conf('media_server_port'), use_https = self.plex.conf('use_https')),
                path,
                self.plex.conf('auth_token')
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

    def createHost(self, host, port = None, use_https = False):

        h = cleanHost(host, True, use_https)
        p = urlparse(h)
        h = h.rstrip('/')

        if port and not p.port:
            h += ':%s' % port

        return h
