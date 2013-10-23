"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


from sleekxmpp.plugins import BasePlugin, register_plugin


class XEP_0106(BasePlugin):

    name = 'xep_0106'
    description = 'XEP-0106: JID Escaping'
    dependencies = set(['xep_0030'])

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature(feature='jid\\20escaping')

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature='jid\\20escaping')


register_plugin(XEP_0106)
