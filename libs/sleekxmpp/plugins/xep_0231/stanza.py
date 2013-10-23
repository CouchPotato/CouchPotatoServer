"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz,
                       Emmanuel Gil Peyrot <linkmauve@linkmauve.fr>
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


from base64 import b64encode, b64decode

from sleekxmpp.xmlstream import ElementBase


class BitsOfBinary(ElementBase):
    name = 'data'
    namespace = 'urn:xmpp:bob'
    plugin_attrib = 'bob'
    interfaces = set(('cid', 'max_age', 'type', 'data'))

    def get_max_age(self):
        return self._get_attr('max-age')

    def set_max_age(self, value):
        self._set_attr('max-age', value)

    def get_data(self):
        return b64decode(self.xml.text)

    def set_data(self, value):
        self.xml.text = b64encode(value)

    def del_data(self):
        self.xml.text = ''
