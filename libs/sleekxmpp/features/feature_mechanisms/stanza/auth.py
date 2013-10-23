"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import base64

from sleekxmpp.util import bytes
from sleekxmpp.xmlstream import StanzaBase


class Auth(StanzaBase):

    """
    """

    name = 'auth'
    namespace = 'urn:ietf:params:xml:ns:xmpp-sasl'
    interfaces = set(('mechanism', 'value'))
    plugin_attrib = name

    #: Some SASL mechs require sending values as is,
    #: without converting base64.
    plain_mechs = set(['X-MESSENGER-OAUTH2'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_value(self):
        if not self['mechanism'] in self.plain_mechs:
            return base64.b64decode(bytes(self.xml.text))
        else:
            return self.xml.text

    def set_value(self, values):
        if not self['mechanism'] in self.plain_mechs:
            if values:
                self.xml.text = bytes(base64.b64encode(values)).decode('utf-8')
            else:
                self.xml.text = '='
        else:
            self.xml.text = bytes(values).decode('utf-8')

    def del_value(self):
        self.xml.text = ''
