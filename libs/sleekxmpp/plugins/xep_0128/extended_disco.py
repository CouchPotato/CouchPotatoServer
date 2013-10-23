"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

import sleekxmpp
from sleekxmpp import Iq
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0004 import Form
from sleekxmpp.plugins.xep_0030 import DiscoInfo
from sleekxmpp.plugins.xep_0128 import StaticExtendedDisco


class XEP_0128(BasePlugin):

    """
    XEP-0128: Service Discovery Extensions

    Allow the use of data forms to add additional identity
    information to disco#info results.

    Also see <http://www.xmpp.org/extensions/xep-0128.html>.

    Attributes:
        disco  -- A reference to the XEP-0030 plugin.
        static -- Object containing the default set of static
                  node handlers.
        xmpp   -- The main SleekXMPP object.

    Methods:
        set_extended_info -- Set extensions to a disco#info result.
        add_extended_info -- Add an extension to a disco#info result.
        del_extended_info -- Remove all extensions from a disco#info result.
    """

    name = 'xep_0128'
    description = 'XEP-0128: Service Discovery Extensions'
    dependencies = set(['xep_0030', 'xep_0004'])

    def plugin_init(self):
        """Start the XEP-0128 plugin."""
        self._disco_ops = ['set_extended_info',
                           'add_extended_info',
                           'del_extended_info']

        register_stanza_plugin(DiscoInfo, Form, iterable=True)

        self.disco = self.xmpp['xep_0030']
        self.static = StaticExtendedDisco(self.disco.static)

        self.disco.set_extended_info = self.set_extended_info
        self.disco.add_extended_info = self.add_extended_info
        self.disco.del_extended_info = self.del_extended_info

        for op in self._disco_ops:
            self.api.register(getattr(self.static, op), op, default=True)

    def set_extended_info(self, jid=None, node=None, **kwargs):
        """
        Set additional, extended identity information to a node.

        Replaces any existing extended information.

        Arguments:
            jid  -- The JID to modify.
            node -- The node to modify.
            data -- Either a form, or a list of forms to use
                    as extended information, replacing any
                    existing extensions.
        """
        self.api['set_extended_info'](jid, node, None, kwargs)

    def add_extended_info(self, jid=None, node=None, **kwargs):
        """
        Add additional, extended identity information to a node.

        Arguments:
            jid  -- The JID to modify.
            node -- The node to modify.
            data -- Either a form, or a list of forms to add
                    as extended information.
        """
        self.api['add_extended_info'](jid, node, None, kwargs)

    def del_extended_info(self, jid=None, node=None, **kwargs):
        """
        Remove all extended identity information to a node.

        Arguments:
            jid  -- The JID to modify.
            node -- The node to modify.
        """
        self.api['del_extended_info'](jid, node, None, kwargs)
