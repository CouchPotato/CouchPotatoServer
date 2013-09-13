from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from urllib2 import URLError
from urlparse import urlparse
from xml.dom import minidom
import traceback

log = CPLog(__name__)


class Plex(Notification):

    def __init__(self):
        super(Plex, self).__init__()
        addEvent('renamer.after', self.addToLibrary)

    def addToLibrary(self, message = None, group = None):
        if self.isDisabled(): return
        if not group: group = {}

        log.info('Sending notification to Plex')
        hosts = self.getHosts(port = 32400)

        for host in hosts:

            source_type = ['movie']
            base_url = '%s/library/sections' % host
            refresh_url = '%s/%%s/refresh' % base_url

            try:
                sections_xml = self.urlopen(base_url)
                xml_sections = minidom.parseString(sections_xml)
                sections = xml_sections.getElementsByTagName('Directory')

                for s in sections:
                    if s.getAttribute('type') in source_type:
                        url = refresh_url % s.getAttribute('key')
                        self.urlopen(url)

            except:
                log.error('Plex library update failed for %s, Media Server not running: %s', (host, traceback.format_exc(1)))
                return False

        return True

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        hosts = self.getHosts(port = 3000)
        successful = 0
        for host in hosts:
            if self.send({'command': 'ExecBuiltIn', 'parameter': 'Notification(CouchPotato, %s)' % message}, host):
                successful += 1

        return successful == len(hosts)

    def send(self, command, host):

        url = '%s/xbmcCmds/xbmcHttp/?%s' % (host, tryUrlencode(command))
        headers = {}

        try:
            self.urlopen(url, headers = headers, show_error = False)
        except URLError:
            log.error("Couldn't sent command to Plex, probably just running Media Server")
            return False
        except:
            log.error("Couldn't sent command to Plex: %s", traceback.format_exc())
            return False

        log.info('Plex notification to %s successful.', host)
        return True

    def test(self, **kwargs):

        test_type = self.testNotifyName()

        log.info('Sending test to %s', test_type)

        success = self.notify(
            message = self.test_message,
            data = {},
            listener = 'test'
        )
        success2 = self.addToLibrary()

        return {
            'success': success or success2
        }

    def getHosts(self, port = None):

        raw_hosts = splitString(self.conf('host'))
        hosts = []

        for h in raw_hosts:
            h = cleanHost(h)
            p = urlparse(h)
            h = h.rstrip('/')
            if port and not p.port:
                h += ':%s' % port
            hosts.append(h)

        return hosts
