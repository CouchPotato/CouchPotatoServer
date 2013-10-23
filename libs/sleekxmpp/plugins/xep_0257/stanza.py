"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET, register_stanza_plugin


class Certs(ElementBase):
    name = 'query'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_certs'
    interfaces = set()


class CertItem(ElementBase):
    name = 'item'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'item'
    plugin_multi_attrib = 'items'
    interfaces = set(['name', 'x509cert', 'users'])
    sub_interfaces = set(['name', 'x509cert'])

    def get_users(self):
        resources = self.xml.findall('{%s}users/{%s}resource' % (
            self.namespace, self.namespace))
        return set([res.text for res in resources])

    def set_users(self, values):
        users = self.xml.find('{%s}users' % self.namespace)
        if users is None:
            users = ET.Element('{%s}users' % self.namespace)
            self.xml.append(users)
        for resource in values:
            res = ET.Element('{%s}resource' % self.namespace)
            res.text = resource
            users.append(res)

    def del_users(self):
        users = self.xml.find('{%s}users' % self.namespace)
        if users is not None:
            self.xml.remove(users)


class AppendCert(ElementBase):
    name = 'append'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_append'
    interfaces = set(['name', 'x509cert', 'cert_management'])
    sub_interfaces = set(['name', 'x509cert'])

    def get_cert_management(self):
        manage = self.xml.find('{%s}no-cert-management' % self.namespace)
        return manage is None

    def set_cert_management(self, value):
        self.del_cert_management()
        if not value:
            manage = ET.Element('{%s}no-cert-management' % self.namespace)
            self.xml.append(manage)

    def del_cert_management(self):
        manage = self.xml.find('{%s}no-cert-management' % self.namespace)
        if manage is not None:
            self.xml.remove(manage)


class DisableCert(ElementBase):
    name = 'disable'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_disable'
    interfaces = set(['name'])
    sub_interfaces = interfaces


class RevokeCert(ElementBase):
    name = 'revoke'
    namespace = 'urn:xmpp:saslcert:1'
    plugin_attrib = 'sasl_cert_revoke'
    interfaces = set(['name'])
    sub_interfaces = interfaces


register_stanza_plugin(Certs, CertItem, iterable=True)
