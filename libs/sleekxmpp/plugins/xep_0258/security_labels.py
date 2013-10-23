"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq, Message
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0258 import stanza, SecurityLabel, Catalog


log = logging.getLogger(__name__)


class XEP_0258(BasePlugin):

    name = 'xep_0258'
    description = 'XEP-0258: Security Labels in XMPP'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, SecurityLabel)
        register_stanza_plugin(Iq, Catalog)

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature=SecurityLabel.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature(SecurityLabel.namespace)

    def get_catalog(self, jid, ifrom=None, block=True,
                          callback=None, timeout=None):
        iq = self.xmpp.Iq()
        iq['to'] = jid
        iq['from'] = ifrom
        iq['type'] = 'get'
        iq.enable('security_label_catalog')
        return iq.send(block=block, callback=callback, timeout=timeout)
