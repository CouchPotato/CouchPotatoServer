from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import base64

log = CPLog(__name__)


class XBMC(Notification):

    listen_to = ['renamer.after']

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        hosts = splitString(self.conf('host'))
        successful = 0
        for host in hosts:
            if self.send({'command': 'ExecBuiltIn', 'parameter': 'Notification(CouchPotato, %s)' % message}, host):
                successful += 1
            if self.send({'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}, host):
                successful += 1

        return successful == len(hosts) * 2

    def send(self, command, host):

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, tryUrlencode(command))

        headers = {}
        if self.conf('password'):
            headers = {
               'Authorization': "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password')))[:-1]
            }

        try:
            self.urlopen(url, headers = headers, show_error = False)
        except:
            log.error("Couldn't sent command to XBMC")
            return False

        log.info('XBMC notification to %s successful.', host)
        return True
