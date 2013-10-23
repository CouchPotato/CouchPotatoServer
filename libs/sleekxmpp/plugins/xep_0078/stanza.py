"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET, register_stanza_plugin


class IqAuth(ElementBase):
    namespace = 'jabber:iq:auth'
    name = 'query'
    plugin_attrib = 'auth'
    interfaces = set(('fields', 'username', 'password', 'resource', 'digest'))
    sub_interfaces = set(('username', 'password', 'resource', 'digest'))
    plugin_tag_map = {}
    plugin_attrib_map = {}

    def get_fields(self):
        fields = set()
        for field in self.sub_interfaces:
            if self.xml.find('{%s}%s' % (self.namespace, field)) is not None:
                fields.add(field)
        return fields

    def set_resource(self, value):
        self._set_sub_text('resource', value, keep=True)

    def set_password(self, value):
        self._set_sub_text('password', value, keep=True)


class AuthFeature(ElementBase):
    namespace = 'http://jabber.org/features/iq-auth'
    name = 'auth'
    plugin_attrib = 'auth'
    interfaces = set()
    plugin_tag_map = {}
    plugin_attrib_map = {}
