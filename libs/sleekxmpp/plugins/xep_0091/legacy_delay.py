"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


from sleekxmpp.stanza import Message, Presence
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0091 import stanza


class XEP_0091(BasePlugin):

    """
    XEP-0091: Legacy Delayed Delivery
    """

    name = 'xep_0091'
    description = 'XEP-0091: Legacy Delayed Delivery'
    dependencies = set()
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, stanza.LegacyDelay)
        register_stanza_plugin(Presence, stanza.LegacyDelay)
