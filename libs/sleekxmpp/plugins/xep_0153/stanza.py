"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase


class VCardTempUpdate(ElementBase):
    name = 'x'
    namespace = 'vcard-temp:x:update'
    plugin_attrib = 'vcard_temp_update'
    interfaces = set(['photo'])
    sub_interfaces = interfaces

    def set_photo(self, value):
        if value is not None:
            self._set_sub_text('photo', value, keep=True)
        else:
            self._del_sub('photo')

    def get_photo(self):
        photo = self.xml.find('{%s}photo' % self.namespace)
        if photo is None:
            return None
        return photo.text
