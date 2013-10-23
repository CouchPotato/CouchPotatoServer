"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Error
from sleekxmpp.xmlstream import ElementBase, StanzaBase


class Enable(StanzaBase):
    name = 'enable'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set(['max', 'resume'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_resume(self):
        return self._get_attr('resume', 'false').lower() in ('true', '1')

    def set_resume(self, val):
        self._del_attr('resume')
        self._set_attr('resume', 'true' if val else 'false')


class Enabled(StanzaBase):
    name = 'enabled'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set(['id', 'location', 'max', 'resume'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_resume(self):
        return self._get_attr('resume', 'false').lower() in ('true', '1')

    def set_resume(self, val):
        self._del_attr('resume')
        self._set_attr('resume', 'true' if val else 'false')


class Resume(StanzaBase):
    name = 'resume'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set(['h', 'previd'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_h(self):
        h = self._get_attr('h', None)
        if h:
            return int(h)
        return None

    def set_h(self, val):
        self._set_attr('h', str(val))


class Resumed(StanzaBase):
    name = 'resumed'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set(['h', 'previd'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_h(self):
        h = self._get_attr('h', None)
        if h:
            return int(h)
        return None

    def set_h(self, val):
        self._set_attr('h', str(val))


class Failed(StanzaBase, Error):
    name = 'failed'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set()

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()


class StreamManagement(ElementBase):
    name = 'sm'
    namespace = 'urn:xmpp:sm:3'
    plugin_attrib = name
    interfaces = set(['required', 'optional'])

    def get_required(self):
        return self.find('{%s}required' % self.namespace) is not None

    def set_required(self, val):
        self.del_required()
        if val:
            self._set_sub_text('required', '', keep=True)

    def del_required(self):
        self._del_sub('required')

    def get_optional(self):
        return self.find('{%s}optional' % self.namespace) is not None

    def set_optional(self, val):
        self.del_optional()
        if val:
            self._set_sub_text('optional', '', keep=True)

    def del_optional(self):
        self._del_sub('optional')


class RequestAck(StanzaBase):
    name = 'r'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set()

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()


class Ack(StanzaBase):
    name = 'a'
    namespace = 'urn:xmpp:sm:3'
    interfaces = set(['h'])

    def setup(self, xml):
        StanzaBase.setup(self, xml)
        self.xml.tag = self.tag_name()

    def get_h(self):
        h = self._get_attr('h', None)
        if h:
            return int(h)
        return None

    def set_h(self, val):
        self._set_attr('h', str(val))
