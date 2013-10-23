"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

import logging

import sleekxmpp
from sleekxmpp.stanza import Message
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0308 import stanza, Replace


log = logging.getLogger(__name__)


class XEP_0308(BasePlugin):

    """
    XEP-0308 Last Message Correction
    """

    name = 'xep_0308'
    description = 'XEP-0308: Last Message Correction'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        self.xmpp.register_handler(
            Callback('Message Correction',
                     StanzaPath('message/replace'),
                     self._handle_correction))

        register_stanza_plugin(Message, Replace)

        self.xmpp.use_message_ids = True

    def plugin_end(self):
        self.xmpp.remove_handler('Message Correction')
        self.xmpp.plugin['xep_0030'].del_feature(feature=Replace.namespace)

    def session_bind(self, jid):
        self.xmpp.plugin['xep_0030'].add_feature(Replace.namespace)

    def _handle_correction(self, msg):
        self.xmpp.event('message_correction', msg)
