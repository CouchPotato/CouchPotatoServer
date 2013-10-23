"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class UserTune(ElementBase):

    name = 'tune'
    namespace = 'http://jabber.org/protocol/tune'
    plugin_attrib = 'tune'
    interfaces = set(['artist', 'length', 'rating', 'source',
                      'title', 'track', 'uri'])
    sub_interfaces = interfaces

    def set_length(self, value):
        self._set_sub_text('length', str(value))

    def set_rating(self, value):
        self._set_sub_text('rating', str(value))
