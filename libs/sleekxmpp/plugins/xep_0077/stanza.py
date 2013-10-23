"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from __future__ import unicode_literals

from sleekxmpp.xmlstream import ElementBase, ET


class Register(ElementBase):

    namespace = 'jabber:iq:register'
    name = 'query'
    plugin_attrib = 'register'
    interfaces = set(('username', 'password', 'email', 'nick', 'name',
                      'first', 'last', 'address', 'city', 'state', 'zip',
                      'phone', 'url', 'date', 'misc', 'text', 'key',
                      'registered', 'remove', 'instructions', 'fields'))
    sub_interfaces = interfaces
    form_fields = set(('username', 'password', 'email', 'nick', 'name',
                       'first', 'last', 'address', 'city', 'state', 'zip',
                       'phone', 'url', 'date', 'misc', 'text', 'key'))

    def get_registered(self):
        present = self.xml.find('{%s}registered' % self.namespace)
        return present is not None

    def get_remove(self):
        present = self.xml.find('{%s}remove' % self.namespace)
        return present is not None

    def set_registered(self, value):
        if value:
            self.add_field('registered')
        else:
            del self['registered']

    def set_remove(self, value):
        if value:
            self.add_field('remove')
        else:
            del self['remove']

    def add_field(self, value):
        self._set_sub_text(value, '', keep=True)

    def get_fields(self):
        fields = set()
        for field in self.form_fields:
            if self.xml.find('{%s}%s' % (self.namespace, field)) is not None:
                fields.add(field)
        return fields

    def set_fields(self, fields):
        del self['fields']
        for field in fields:
            self._set_sub_text(field, '', keep=True)

    def del_fields(self):
        for field in self.form_fields:
            self._del_sub(field)


class RegisterFeature(ElementBase):

    name = 'register'
    namespace = 'http://jabber.org/features/iq-register'
    plugin_attrib = name
    interfaces = set()
