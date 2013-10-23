from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from libs.sleekxmpp import ClientXMPP
from time import sleep
import traceback

log = CPLog(__name__)


class Xmpp(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        try:
            xmpp = ClientXMPP(self.conf('username'), self.conf('password'))

            def on_start(e):
                xmpp.send_message(mto=self.conf('to'), mbody=message, mtype='chat')
                xmpp.disconnect(wait=True)
            xmpp.add_event_handler('session_start', on_start)

            # Connect
            for _ in range(5):
                if xmpp.connect(address=(self.conf('hostname'), self.conf('port')), reattempt=False,
                                use_tls=self.conf('use_tls'), use_ssl=self.conf('use_ssl')):
                    xmpp.process(block=True)
                    sleep(1)

                    log.info('XMPP notifications sent.')
                    return True
                sleep(1)

            log.error('XMPP failed: Connection failed, check login.')
        except:
            log.error('XMPP failed: %s', traceback.format_exc())

        return False
