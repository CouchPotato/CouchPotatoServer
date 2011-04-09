from couchpotato.api import addApiView
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.core.notifications.growl.growl import GROWL_UDP_PORT, \
    GrowlRegistrationPacket, GrowlNotificationPacket
from couchpotato.environment import Env
from socket import AF_INET, SOCK_DGRAM, socket

log = CPLog(__name__)


class Growl(Notification):

    def __init__(self):
        addEvent('notify', self.notify)
        addEvent('notify.growl', self.notify)

        addApiView('notify.growl.test', self.test)

    def conf(self, attr):
        return Env.setting(attr, 'growl')

    def notify(self, message = '', data = {}):

        if self.isDisabled():
            return

        hosts = [x.strip() for x in self.conf('host').split(",")]
        password = self.conf('password')

        for curHost in hosts:
            addr = (curHost, GROWL_UDP_PORT)

            s = socket(AF_INET, SOCK_DGRAM)
            p = GrowlRegistrationPacket(password = password)
            p.addNotification()
            s.sendto(p.payload(), addr)

            # send notification
            p = GrowlNotificationPacket(title = self.default_title, description = message, priority = 0, sticky = False, password = password)
            s.sendto(p.payload(), addr)
            s.close()

            log.info('Growl notifications sent.')
