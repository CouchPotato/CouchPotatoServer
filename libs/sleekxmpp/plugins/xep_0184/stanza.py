"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Erik Reuterborg Larsson, Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream.stanzabase import ElementBase, ET


class Request(ElementBase):
    namespace = 'urn:xmpp:receipts'
    name = 'request'
    plugin_attrib = 'request_receipt'
    interfaces = set(('request_receipt',))
    sub_interfaces = interfaces
    is_extension = True

    def setup(self, xml=None):
        self.xml = ET.Element('')
        return True

    def set_request_receipt(self, val):
        self.del_request_receipt()
        if val:
            parent = self.parent()
            parent._set_sub_text("{%s}request" % self.namespace, keep=True)
            if not parent['id']:
                if parent.stream:
                    parent['id'] = parent.stream.new_id()

    def get_request_receipt(self):
        parent = self.parent()
        if parent.find("{%s}request" % self.namespace) is not None:
            return True
        else:
            return False

    def del_request_receipt(self):
        self.parent()._del_sub("{%s}request" % self.namespace)


class Received(ElementBase):
    namespace = 'urn:xmpp:receipts'
    name = 'received'
    plugin_attrib = 'receipt'
    interfaces = set(['receipt'])
    sub_interfaces = interfaces
    is_extension = True

    def setup(self, xml=None):
        self.xml = ET.Element('')
        return True

    def set_receipt(self, value):
        self.del_receipt()
        if value:
            parent = self.parent()
            xml = ET.Element("{%s}received" % self.namespace)
            xml.attrib['id'] = value
            parent.append(xml)

    def get_receipt(self):
        parent = self.parent()
        xml = parent.find("{%s}received" % self.namespace)
        if xml is not None:
            return xml.attrib.get('id', '')
        return ''

    def del_receipt(self):
        self.parent()._del_sub('{%s}received' % self.namespace)
