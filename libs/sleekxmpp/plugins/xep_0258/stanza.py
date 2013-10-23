"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from base64 import b64encode, b64decode

from sleekxmpp.util import bytes
from sleekxmpp.xmlstream import ElementBase, ET, register_stanza_plugin


class SecurityLabel(ElementBase):
    name = 'securitylabel'
    namespace = 'urn:xmpp:sec-label:0'
    plugin_attrib = 'security_label'

    def add_equivalent(self, label):
        equiv = EquivalentLabel(parent=self)
        equiv.append(label)
        return equiv


class Label(ElementBase):
    name = 'label'
    namespace = 'urn:xmpp:sec-label:0'
    plugin_attrib = 'label'


class DisplayMarking(ElementBase):
    name = 'displaymarking'
    namespace = 'urn:xmpp:sec-label:0'
    plugin_attrib = 'display_marking'
    interfaces = set(['fgcolor', 'bgcolor', 'value'])

    def get_fgcolor(self):
        return self._get_attr('fgcolor', 'black')

    def get_bgcolor(self):
        return self._get_attr('fgcolor', 'white')

    def get_value(self):
        return self.xml.text

    def set_value(self, value):
        self.xml.text = value

    def del_value(self):
        self.xml.text = ''


class EquivalentLabel(ElementBase):
    name = 'equivalentlabel'
    namespace = 'urn:xmpp:sec-label:0'
    plugin_attrib = 'equivalent_label'
    plugin_multi_attrib = 'equivalent_labels'


class Catalog(ElementBase):
    name = 'catalog'
    namespace = 'urn:xmpp:sec-label:catalog:2'
    plugin_attrib = 'security_label_catalog'
    interfaces = set(['to', 'from', 'name', 'desc', 'id', 'size', 'restrict'])

    def get_to(self):
        return JID(self._get_attr('to'))
        pass

    def set_to(self, value):
        return self._set_attr('to', str(value))

    def get_from(self):
        return JID(self._get_attr('from'))

    def set_from(self, value):
        return self._set_attr('from', str(value))

    def get_restrict(self):
        value = self._get_attr('restrict', '')
        if value and value.lower() in ('true', '1'):
            return True
        return False

    def set_restrict(self, value):
        self._del_attr('restrict')
        if value:
            self._set_attr('restrict', 'true')
        elif value is False:
            self._set_attr('restrict', 'false')


class CatalogItem(ElementBase):
    name = 'catalog'
    namespace = 'urn:xmpp:sec-label:catalog:2'
    plugin_attrib = 'item'
    plugin_multi_attrib = 'items'
    interfaces = set(['selector', 'default'])

    def get_default(self):
        value = self._get_attr('default', '')
        if value.lower() in ('true', '1'):
            return True
        return False

    def set_default(self, value):
        self._del_attr('default')
        if value:
            self._set_attr('default', 'true')
        elif value is False:
            self._set_attr('default', 'false')


class ESSLabel(ElementBase):
    name = 'esssecuritylabel'
    namespace = 'urn:xmpp:sec-label:ess:0'
    plugin_attrib = 'ess'
    interfaces = set(['value'])

    def get_value(self):
        if self.xml.text:
            return b64decode(bytes(self.xml.text))
        return ''

    def set_value(self, value):
        self.xml.text = ''
        if value:
            self.xml.text = b64encode(bytes(value))

    def del_value(self):
        self.xml.text = ''


register_stanza_plugin(Catalog, CatalogItem, iterable=True)
register_stanza_plugin(CatalogItem, SecurityLabel)
register_stanza_plugin(EquivalentLabel, ESSLabel)
register_stanza_plugin(Label, ESSLabel)
register_stanza_plugin(SecurityLabel, DisplayMarking)
register_stanza_plugin(SecurityLabel, EquivalentLabel, iterable=True)
register_stanza_plugin(SecurityLabel, Label)
