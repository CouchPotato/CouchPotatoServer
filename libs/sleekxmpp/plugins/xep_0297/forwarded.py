"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


import logging

from sleekxmpp import Iq, Message, Presence
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins.xep_0297 import stanza, Forwarded


class XEP_0297(BasePlugin):

    name = 'xep_0297'
    description = 'XEP-0297: Stanza Forwarding'
    dependencies = set(['xep_0030', 'xep_0203'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, Forwarded)

        # While these are marked as iterable, that is just for
        # making it easier to extract the forwarded stanza. There
        # still can be only a single forwarded stanza.
        register_stanza_plugin(Forwarded, Message, iterable=True)
        register_stanza_plugin(Forwarded, Presence, iterable=True)
        register_stanza_plugin(Forwarded, Iq, iterable=True)

        register_stanza_plugin(Forwarded, self.xmpp['xep_0203'].stanza.Delay)

        self.xmpp.register_handler(
            Callback('Forwarded Stanza',
                StanzaPath('message/forwarded'),
                self._handle_forwarded))

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('urn:xmpp:forward:0')

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature='urn:xmpp:forward:0')
        self.xmpp.remove_handler('Forwarded Stanza')

    def forward(self, stanza=None, mto=None, mbody=None, mfrom=None, delay=None):
        stanza.stream = None

        msg = self.xmpp.Message()
        msg['to'] = mto
        msg['from'] = mfrom
        msg['body'] = mbody
        msg['forwarded']['stanza'] = stanza
        if delay is not None:
            msg['forwarded']['delay']['stamp'] = delay
        msg.send()

    def _handle_forwarded(self, msg):
        self.xmpp.event('forwarded_stanza', msg)
