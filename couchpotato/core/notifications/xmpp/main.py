from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from time import sleep
import traceback
import xmpp

log = CPLog(__name__)


class Xmpp(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            jid = xmpp.protocol.JID(self.conf('username'))
            client = xmpp.Client(jid.getDomain(), debug = [])

            # Connect
            if not client.connect(server = (self.conf('hostname'), self.conf('port'))):
                log.error('XMPP failed: Connection to server failed.')
                return False

            # Authenticate
            if not client.auth(jid.getNode(), self.conf('password'), resource = jid.getResource()):
                log.error('XMPP failed: Failed to authenticate.')
                return False

            # Send message
            client.send(xmpp.protocol.Message(to = self.conf('to'), body = message, typ = 'chat'))

            # Disconnect
            # some older servers will not send the message if you disconnect immediately after sending
            sleep(1)
            client.disconnect()

            log.info('XMPP notifications sent.')
            return True

        except:
            log.error('XMPP failed: %s', traceback.format_exc())

        return False
