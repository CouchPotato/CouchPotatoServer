"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

from sleekxmpp.jid import JID
from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin


class Offline(ElementBase):
    name = 'offline'
    namespace = 'http://jabber.org/protocol/offline'
    plugin_attrib = 'offline'
    interfaces = set(['fetch', 'purge', 'results'])
    bool_interfaces = interfaces

    def setup(self, xml=None):
        ElementBase.setup(self, xml)
        self._results = []

    # The results interface is meant only as an easy
    # way to access the set of collected message responses
    # from the query.

    def get_results(self):
        return self._results

    def set_results(self, values):
        self._results = values

    def del_results(self):
        self._results = []


class Item(ElementBase):
    name = 'item'
    namespace = 'http://jabber.org/protocol/offline'
    plugin_attrib = 'item'
    interfaces = set(['action', 'node', 'jid'])

    actions = set(['view', 'remove'])

    def get_jid(self):
        return JID(self._get_attr('jid'))

    def set_jid(self, value):
        self._set_attr('jid', str(value))


register_stanza_plugin(Offline, Item, iterable=True)
