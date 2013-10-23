"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Attention(ElementBase):

    """
    """

    name = 'attention'
    namespace = 'urn:xmpp:attention:0'
    plugin_attrib = 'attention'
    interfaces = set(('attention',))
    is_extension = True

    def setup(self, xml):
        return True

    def set_attention(self, value):
        if value:
            xml = ET.Element(self.tag_name())
            self.parent().xml.append(xml)
        else:
            self.del_attention()

    def get_attention(self):
        xml = self.parent().xml.find(self.tag_name())
        return xml is not None

    def del_attention(self):
        xml = self.parent().xml.find(self.tag_name())
        if xml is not None:
            self.parent().xml.remove(xml)
