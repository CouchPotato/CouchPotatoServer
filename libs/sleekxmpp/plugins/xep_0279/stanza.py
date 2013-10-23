"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class IPCheck(ElementBase):

    name = 'ip'
    namespace = 'urn:xmpp:sic:0'
    plugin_attrib = 'ip_check'
    interfaces = set(['ip_check'])
    is_extension = True

    def get_ip_check(self):
        return self.xml.text

    def set_ip_check(self, value):
        if value:
            self.xml.text = value
        else:
            self.xml.text = ''

    def del_ip_check(self):
        self.xml.text = ''
