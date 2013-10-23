"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


import logging

from sleekxmpp import Iq
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0279 import stanza, IPCheck


class XEP_0279(BasePlugin):

    name = 'xep_0279'
    description = 'XEP-0279: Server IP Check'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, IPCheck)

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('urn:xmpp:sic:0')

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature='urn:xmpp:sic:0')

    def check_ip(self, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['from'] = ifrom
        iq.enable('ip_check')
        return iq.send(block=block, timeout=timeout, callback=callback)
