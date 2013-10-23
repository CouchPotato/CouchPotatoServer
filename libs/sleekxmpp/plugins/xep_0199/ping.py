"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import time
import logging

import sleekxmpp
from sleekxmpp import Iq
from sleekxmpp.exceptions import IqError, IqTimeout
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0199 import stanza, Ping


log = logging.getLogger(__name__)


class XEP_0199(BasePlugin):

    """
    XEP-0199: XMPP Ping

    Given that XMPP is based on TCP connections, it is possible for the
    underlying connection to be terminated without the application's
    awareness. Ping stanzas provide an alternative to whitespace based
    keepalive methods for detecting lost connections.

    Also see <http://www.xmpp.org/extensions/xep-0199.html>.

    Attributes:
        keepalive -- If True, periodically send ping requests
                     to the server. If a ping is not answered,
                     the connection will be reset.
        frequency -- Time in seconds between keepalive pings.
                     Defaults to 300 seconds.
        timeout   -- Time in seconds to wait for a ping response.
                     Defaults to 30 seconds.
    Methods:
        send_ping -- Send a ping to a given JID, returning the
                     round trip time.
    """

    name = 'xep_0199'
    description = 'XEP-0199: XMPP Ping'
    dependencies = set(['xep_0030'])
    stanza = stanza
    default_config = {
        'keepalive': False,
        'frequency': 300,
        'timeout': 30
    }

    def plugin_init(self):
        """
        Start the XEP-0199 plugin.
        """
        register_stanza_plugin(Iq, Ping)

        self.xmpp.register_handler(
                Callback('Ping',
                         StanzaPath('iq@type=get/ping'),
                         self._handle_ping))

        if self.keepalive:
            self.xmpp.add_event_handler('session_start',
                                        self._handle_keepalive,
                                        threaded=True)
            self.xmpp.add_event_handler('session_end',
                                        self._handle_session_end)

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature=Ping.namespace)
        self.xmpp.remove_handler('Ping')
        if self.keepalive:
            self.xmpp.del_event_handler('session_start',
                                        self._handle_keepalive)
            self.xmpp.del_event_handler('session_end',
                                        self._handle_session_end)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature(Ping.namespace)

    def _handle_keepalive(self, event):
        """
        Begin periodic pinging of the server. If a ping is not
        answered, the connection will be restarted.

        The pinging interval can be adjused using self.frequency
        before beginning processing.

        Arguments:
            event -- The session_start event.
        """
        def scheduled_ping():
            """Send ping request to the server."""
            log.debug("Pinging...")
            try:
                self.send_ping(self.xmpp.boundjid.host, self.timeout)
            except IqError:
                log.debug("Ping response was an error." + \
                          "Requesting Reconnect.")
                self.xmpp.reconnect()
            except IqTimeout:
                log.debug("Did not recieve ping back in time." + \
                          "Requesting Reconnect.")
                self.xmpp.reconnect()

        self.xmpp.schedule('Ping Keep Alive',
                           self.frequency,
                           scheduled_ping,
                           repeat=True)

    def _handle_session_end(self, event):
        self.xmpp.scheduler.remove('Ping Keep Alive')

    def _handle_ping(self, iq):
        """
        Automatically reply to ping requests.

        Arguments:
            iq -- The ping request.
        """
        log.debug("Pinged by %s", iq['from'])
        iq.reply().send()

    def send_ping(self, jid, timeout=None, errorfalse=False,
                  ifrom=None, block=True, callback=None):
        """
        Send a ping request and calculate the response time.

        Arguments:
            jid        -- The JID that will receive the ping.
            timeout    -- Time in seconds to wait for a response.
                          Defaults to self.timeout.
            errorfalse -- Indicates if False should be returned
                          if an error stanza is received. Defaults
                          to False.
            ifrom      -- Specifiy the sender JID.
            block      -- Indicate if execution should block until
                          a pong response is received. Defaults
                          to True.
            callback   -- Optional handler to execute when a pong
                          is received. Useful in conjunction with
                          the option block=False.
        """
        log.debug("Pinging %s", jid)
        if timeout is None:
            timeout = self.timeout

        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['to'] = jid
        iq['from'] = ifrom
        iq.enable('ping')

        start_time = time.clock()

        try:
            resp = iq.send(block=block,
                           timeout=timeout,
                           callback=callback)
        except IqError as err:
            resp = err.iq

        end_time = time.clock()

        delay = end_time - start_time

        if not block:
            return None

        log.debug("Pong: %s %f", jid, delay)
        return delay
