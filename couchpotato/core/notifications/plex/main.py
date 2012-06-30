from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from xml.dom import minidom
import traceback

log = CPLog(__name__)


class Plex(Notification):

    def __init__(self):
        super(Plex, self).__init__()
        addEvent('renamer.after', self.addToLibrary)

    def addToLibrary(self, group = {}):
        if self.isDisabled(): return

        log.info('Sending notification to Plex')
        hosts = [cleanHost(x.strip() + ':32400') for x in self.conf('host').split(",")]

        for host in hosts:

            source_type = ['movie']
            base_url = '%slibrary/sections' % host
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
                log.error('Plex library update failed for %s: %s', (host, traceback.format_exc()))
                return False

        return True

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        hosts = [x.strip() + ':3000' for x in self.conf('host').split(",")]
        successful = 0
        for host in hosts:
            if self.send({'command': 'ExecBuiltIn', 'parameter': 'Notification(CouchPotato, %s)' % message}, host):
                successful += 1

        return successful == len(hosts)

    def send(self, command, host):

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, tryUrlencode(command))

        headers = {}

        try:
            self.urlopen(url, headers = headers, show_error = False)
        except:
            log.error("Couldn't sent command to Plex: %s", traceback.format_exc())
            return False

        log.info('Plex notification to %s successful.', host)
        return True
