"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.stanza import Message, Presence, Iq
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0066 import stanza


log = logging.getLogger(__name__)


class XEP_0066(BasePlugin):

    """
    XEP-0066: Out of Band Data

    Out of Band Data is a basic method for transferring files between
    XMPP agents. The URL of the resource in question is sent to the receiving
    entity, which then downloads the resource before responding to the OOB
    request. OOB is also used as a generic means to transmit URLs in other
    stanzas to indicate where to find additional information.

    Also see <http://www.xmpp.org/extensions/xep-0066.html>.

    Events:
        oob_transfer -- Raised when a request to download a resource
                        has been received.

    Methods:
        send_oob -- Send a request to another entity to download a file
                    or other addressable resource.
    """

    name = 'xep_0066'
    description = 'XEP-0066: Out of Band Data'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        """Start the XEP-0066 plugin."""

        self.url_handlers = {'global': self._default_handler,
                             'jid': {}}

        register_stanza_plugin(Iq, stanza.OOBTransfer)
        register_stanza_plugin(Message, stanza.OOB)
        register_stanza_plugin(Presence, stanza.OOB)

        self.xmpp.register_handler(
                Callback('OOB Transfer',
                         StanzaPath('iq@type=set/oob_transfer'),
                         self._handle_transfer))

    def plugin_end(self):
        self.xmpp.remove_handler('OOB Transfer')
        self.xmpp['xep_0030'].del_feature(feature=stanza.OOBTransfer.namespace)
        self.xmpp['xep_0030'].del_feature(feature=stanza.OOB.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature(stanza.OOBTransfer.namespace)
        self.xmpp['xep_0030'].add_feature(stanza.OOB.namespace)

    def register_url_handler(self, jid=None, handler=None):
        """
        Register a handler to process download requests, either for all
        JIDs or a single JID.

        Arguments:
            jid     -- If None, then set the handler as a global default.
            handler -- If None, then remove the existing handler for the
                       given JID, or reset the global handler if the JID
                       is None.
        """
        if jid is None:
            if handler is not None:
                self.url_handlers['global'] = handler
            else:
                self.url_handlers['global'] = self._default_handler
        else:
            if handler is not None:
                self.url_handlers['jid'][jid] = handler
            else:
                del self.url_handlers['jid'][jid]

    def send_oob(self, to, url, desc=None, ifrom=None, **iqargs):
        """
        Initiate a basic file transfer by sending the URL of
        a file or other resource.

        Arguments:
            url      -- The URL of the resource to transfer.
            desc     -- An optional human readable description of the item
                        that is to be transferred.
            ifrom    -- Specifiy the sender's JID.
            block    -- If true, block and wait for the stanzas' reply.
            timeout  -- The time in seconds to block while waiting for
                        a reply. If None, then wait indefinitely.
            callback -- Optional callback to execute when a reply is
                        received instead of blocking and waiting for
                        the reply.
        """
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['to'] = to
        iq['from'] = ifrom
        iq['oob_transfer']['url'] = url
        iq['oob_transfer']['desc'] = desc
        return iq.send(**iqargs)

    def _run_url_handler(self, iq):
        """
        Execute the appropriate handler for a transfer request.

        Arguments:
            iq -- The Iq stanza containing the OOB transfer request.
        """
        if iq['to'] in self.url_handlers['jid']:
            return self.url_handlers['jid'][iq['to']](iq)
        else:
            if self.url_handlers['global']:
                self.url_handlers['global'](iq)
            else:
                raise XMPPError('service-unavailable')

    def _default_handler(self, iq):
        """
        As a safe default, don't actually download files.

        Register a new handler using self.register_url_handler to
        screen requests and download files.

        Arguments:
            iq -- The Iq stanza containing the OOB transfer request.
        """
        raise XMPPError('service-unavailable')

    def _handle_transfer(self, iq):
        """
        Handle receiving an out-of-band transfer request.

        Arguments:
            iq -- An Iq stanza containing an OOB transfer request.
        """
        log.debug('Received out-of-band data request for %s from %s:' % (
            iq['oob_transfer']['url'], iq['from']))
        self._run_url_handler(iq)
        iq.reply().send()
