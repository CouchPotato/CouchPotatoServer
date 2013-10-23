"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Erik Reuterborg Larsson, Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.stanza import Message
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0184 import stanza, Request, Received


class XEP_0184(BasePlugin):

    """
    XEP-0184: Message Delivery Receipts
    """

    name = 'xep_0184'
    description = 'XEP-0184: Message Delivery Receipts'
    dependencies = set(['xep_0030'])
    stanza = stanza
    default_config = {
        'auto_ack': True,
        'auto_request': False
    }

    ack_types = ('normal', 'chat', 'headline')

    def plugin_init(self):
        register_stanza_plugin(Message, Request)
        register_stanza_plugin(Message, Received)

        self.xmpp.add_filter('out', self._filter_add_receipt_request)

        self.xmpp.register_handler(
                Callback('Message Receipt',
                    StanzaPath('message/receipt'),
                    self._handle_receipt_received))

        self.xmpp.register_handler(
                Callback('Message Receipt Request',
                    StanzaPath('message/request_receipt'),
                    self._handle_receipt_request))

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature('urn:xmpp:receipts')
        self.xmpp.del_filter('out', self._filter_add_receipt_request)
        self.xmpp.remove_handler('Message Receipt')
        self.xmpp.remove_handler('Message Receipt Request')

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('urn:xmpp:receipts')

    def ack(self, msg):
        """
        Acknowledge a message by sending a receipt.

        Arguments:
            msg -- The message to acknowledge.
        """
        ack = self.xmpp.Message()
        ack['to'] = msg['from']
        ack['from'] = msg['to']
        ack['receipt'] = msg['id']
        ack['id'] = msg['id']
        ack.send()

    def _handle_receipt_received(self, msg):
        self.xmpp.event('receipt_received', msg)

    def _handle_receipt_request(self, msg):
        """
        Auto-ack message receipt requests if ``self.auto_ack`` is ``True``.

        Arguments:
            msg -- The incoming message requesting a receipt.
        """
        if self.auto_ack:
            if msg['type'] in self.ack_types:
                if not msg['receipt']:
                    self.ack(msg)

    def _filter_add_receipt_request(self, stanza):
        """
        Auto add receipt requests to outgoing messages, if:

            - ``self.auto_request`` is set to ``True``
            - The message is not for groupchat
            - The message does not contain a receipt acknowledgment
            - The recipient is a bare JID or, if a full JID, one
              that has the ``urn:xmpp:receipts`` feature enabled

        The disco cache is checked if a full JID is specified in
        the outgoing message, which may mean a round-trip disco#info
        delay for the first message sent to the JID if entity caps
        are not used.
        """

        if not self.auto_request:
            return stanza

        if not isinstance(stanza, Message):
            return stanza

        if stanza['request_receipt']:
            return stanza

        if not stanza['type'] in self.ack_types:
            return stanza

        if stanza['receipt']:
            return stanza

        if stanza['to'].resource:
            if not self.xmpp['xep_0030'].supports(stanza['to'],
                    feature='urn:xmpp:receipts',
                    cached=True):
                return stanza

        stanza['request_receipt'] = True
        return stanza
