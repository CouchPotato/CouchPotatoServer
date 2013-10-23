"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import base64

from sleekxmpp.util import bytes
from sleekxmpp.xmlstream import StanzaBase

class Success(StanzaBase):

    """
    """

    name = 'success'
    namespace = 'urn:ietf:params:xml:ns:xmpp-sasl'
    interfaces = set(['value'])
    plugin_attrib = name

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_value(self):
        return base64.b64decode(bytes(self.xml.text))

    def set_value(self, values):
        if values:
            self.xml.text = bytes(base64.b64encode(values)).decode('utf-8')
        else:
            self.xml.text = '='

    def del_value(self):
        self.xml.text = ''
