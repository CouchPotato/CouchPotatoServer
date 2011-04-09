from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import base64
import urllib
import urllib2

log = CPLog(__name__)


class XBMC(Notification):

    def __init__(self):
        addEvent('notify', self.notify)
        addEvent('notify.xbmc', self.notify)

        addApiView('notify.xbmc.test', self.test)

    def notify(self, message = '', data = {}):

        if self.isDisabled():
            return

        for host in [x.strip() for x in self.conf('host').split(",")]:
            self.send({'command': 'ExecBuiltIn', 'parameter': 'Notification(CouchPotato, %s)' % message}, host)
            self.send({'command': 'ExecBuiltIn', 'parameter': 'XBMC.updatelibrary(video)'}, host)

        return True

    def send(self, command, host):

        url = 'http://%s/xbmcCmds/xbmcHttp/?%s' % (host, urllib.urlencode(command))

        try:
            req = urllib2.Request(url)
            if self.password:
                authHeader = "Basic %s" % base64.encodestring('%s:%s' % (self.conf('username'), self.conf('password')))[:-1]
                req.add_header("Authorization", authHeader)

            urllib2.urlopen(req, timeout = 10).read()
        except Exception, e:
            log.error("Couldn't sent command to XBMC. %s" % e)
            return False

        log.info('XBMC notification to %s successful.' % host)
        return True
