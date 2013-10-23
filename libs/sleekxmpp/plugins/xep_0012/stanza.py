"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class LastActivity(ElementBase):

    name = 'query'
    namespace = 'jabber:iq:last'
    plugin_attrib = 'last_activity'
    interfaces = set(('seconds', 'status'))

    def get_seconds(self):
        return int(self._get_attr('seconds'))

    def set_seconds(self, value):
        self._set_attr('seconds', str(value))

    def get_status(self):
        return self.xml.text

    def set_status(self, value):
        self.xml.text = str(value)

    def del_status(self):
        self.xml.text = ''
