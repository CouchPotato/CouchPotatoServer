"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import datetime as dt

from sleekxmpp.xmlstream import ElementBase
from sleekxmpp.plugins import xep_0082


class Delay(ElementBase):

    name = 'delay'
    namespace = 'urn:xmpp:delay'
    plugin_attrib = 'delay'
    interfaces = set(('from', 'stamp', 'text'))

    def get_from(self):
        return JID(self._get_attr('from'))

    def set_from(self, value):
        self._set_attr('from', str(value))

    def get_stamp(self):
        timestamp = self._get_attr('stamp')
        return xep_0082.parse(timestamp)

    def set_stamp(self, value):
        if isinstance(value, dt.datetime):
            value = xep_0082.format_datetime(value)
        self._set_attr('stamp', value)

    def get_text(self):
        return self.xml.text

    def set_text(self, value):
        self.xml.text = value

    def del_text(self):
        self.xml.text = ''
