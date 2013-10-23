"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class Signed(ElementBase):
    name = 'x'
    namespace = 'jabber:x:signed'
    plugin_attrib = 'signed'
    interfaces = set(['signed'])
    is_extension = True

    def set_signed(self, value):
        parent = self.parent()
        xmpp = parent.stream
        data = xmpp['xep_0027'].sign(value, parent['from'])
        if data:
            self.xml.text = data
        else:
            del parent['signed']

    def get_signed(self):
        return self.xml.text


class Encrypted(ElementBase):
    name = 'x'
    namespace = 'jabber:x:encrypted'
    plugin_attrib = 'encrypted'
    interfaces = set(['encrypted'])
    is_extension = True

    def set_encrypted(self, value):
        parent = self.parent()
        xmpp = parent.stream
        data = xmpp['xep_0027'].encrypt(value, parent['to'].bare)
        if data:
            self.xml.text = data
        else:
            del parent['encrypted']

    def get_encrypted(self):
        parent = self.parent()
        xmpp = parent.stream
        if self.xml.text:
            return xmpp['xep_0027'].decrypt(self.xml.text, parent['to'])
        return None
