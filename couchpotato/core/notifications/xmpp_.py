from time import sleep
import traceback

from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
import xmpp


log = CPLog(__name__)

autoload = 'Xmpp'


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


config = [{
    'name': 'xmpp',
    'groups': [
        {
            'tab': 'notifications',
            'list': 'notification_providers',
            'name': 'xmpp',
            'label': 'XMPP',
            'description`': 'for Jabber, Hangouts (Google Talk), AIM...',
            'options': [
                {
                    'name': 'enabled',
                    'default': 0,
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'description': 'User sending the message. For Hangouts, e-mail of a single-step authentication Google account.',
                },
                {
                    'name': 'password',
                    'type': 'Password',
                },
                {
                    'name': 'hostname',
                    'default': 'talk.google.com',
                },
                {
                    'name': 'to',
                    'description': 'Username (or e-mail for Hangouts) of the person to send the messages to.',
                },
                {
                    'name': 'port',
                    'type': 'int',
                    'default': 5222,
                },
                {
                    'name': 'on_snatch',
                    'default': 0,
                    'type': 'bool',
                    'advanced': True,
                    'description': 'Also send message when movie is snatched.',
                },
            ],
        }
    ],
}]
