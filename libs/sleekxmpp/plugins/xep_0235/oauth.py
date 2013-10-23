"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


import logging

from sleekxmpp import Message
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0235 import stanza, OAuth


class XEP_0235(BasePlugin):

    name = 'xep_0235'
    description = 'XEP-0235: OAuth Over XMPP'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, OAuth)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('urn:xmpp:oauth:0')

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature='urn:xmpp:oauth:0')
