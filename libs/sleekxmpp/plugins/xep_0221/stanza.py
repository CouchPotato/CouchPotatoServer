"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin


class Media(ElementBase):
    name = 'media'
    namespace = 'urn:xmpp:media-element'
    plugin_attrib = 'media'
    interfaces = set(['height', 'width', 'alt'])

    def add_uri(self, value, itype):
        uri = URI()
        uri['value'] = value
        uri['type'] = itype
        self.append(uri)


class URI(ElementBase):
    name = 'uri'
    namespace = 'urn:xmpp:media-element'
    plugin_attrib = 'uri'
    plugin_multi_attrib = 'uris'
    interfaces = set(['type', 'value'])

    def get_value(self):
        return self.xml.text

    def set_value(self, value):
        self.xml.text = value

    def del_value(self):
        sel.xml.text = ''


register_stanza_plugin(Media, URI, iterable=True)
