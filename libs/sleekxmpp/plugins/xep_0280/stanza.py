"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

from sleekxmpp.xmlstream import ElementBase


class ReceivedCarbon(ElementBase):
    name = 'received'
    namespace = 'urn:xmpp:carbons:2'
    plugin_attrib = 'carbon_received'
    interfaces = set(['carbon_received'])
    is_extension = True

    def get_carbon_received(self):
        return self['forwarded']['stanza']

    def del_carbon_received(self):
        del self['forwarded']['stanza']

    def set_carbon_received(self, stanza):
        self['forwarded']['stanza'] = stanza


class SentCarbon(ElementBase):
    name = 'sent'
    namespace = 'urn:xmpp:carbons:2'
    plugin_attrib = 'carbon_sent'
    interfaces = set(['carbon_sent'])
    is_extension = True

    def get_carbon_sent(self):
        return self['forwarded']['stanza']

    def del_carbon_sent(self):
        del self['forwarded']['stanza']

    def set_carbon_sent(self, stanza):
        self['forwarded']['stanza'] = stanza


class PrivateCarbon(ElementBase):
    name = 'private'
    namespace = 'urn:xmpp:carbons:2'
    plugin_attrib = 'carbon_private'
    interfaces = set()


class CarbonEnable(ElementBase):
    name = 'enable'
    namespace = 'urn:xmpp:carbons:2'
    plugin_attrib = 'carbon_enable'
    interfaces = set()


class CarbonDisable(ElementBase):
    name = 'disable'
    namespace = 'urn:xmpp:carbons:2'
    plugin_attrib = 'carbon_disable'
    interfaces = set()
