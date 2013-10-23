"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream import register_stanza_plugin, JID
from sleekxmpp.plugins.xep_0191 import stanza, Block, Unblock, BlockList


log = logging.getLogger(__name__)


class XEP_0191(BasePlugin):

    name = 'xep_0191'
    description = 'XEP-0191: Blocking Command'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, BlockList)
        register_stanza_plugin(Iq, Block)
        register_stanza_plugin(Iq, Unblock)

        self.xmpp.register_handler(
                Callback('Blocked Contact',
                    StanzaPath('iq@type=set/block'),
                    self._handle_blocked))

        self.xmpp.register_handler(
                Callback('Unblocked Contact',
                    StanzaPath('iq@type=set/unblock'),
                    self._handle_unblocked))

    def plugin_end(self):
        self.xmpp.remove_handler('Blocked Contact')
        self.xmpp.remove_handler('Unblocked Contact')

    def get_blocked(self, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['from'] = ifrom
        iq.enable('blocklist')
        return iq.send(block=block, timeout=timeout, callback=callback)

    def block(self, jids, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom

        if not isinstance(jids, (set, list)):
            jids = [jids]

        iq['block']['items'] = jids
        return iq.send(block=block, timeout=timeout, callback=callback)

    def unblock(self, jids=None, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom

        if jids is None:
            jids = []
        if not isinstance(jids, (set, list)):
            jids = [jids]

        iq['unblock']['items'] = jids
        return iq.send(block=block, timeout=timeout, callback=callback)

    def _handle_blocked(self, iq):
        self.xmpp.event('blocked', iq)

    def _handle_unblocked(self, iq):
        self.xmpp.event('unblocked', iq)
