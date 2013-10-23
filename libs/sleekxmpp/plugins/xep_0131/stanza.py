"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.thirdparty import OrderedDict
from sleekxmpp.xmlstream import ET, ElementBase


class Headers(ElementBase):
    name = 'headers'
    namespace = 'http://jabber.org/protocol/shim'
    plugin_attrib = 'headers'
    interfaces = set(['headers'])
    is_extension = True

    def get_headers(self):
        result = OrderedDict()
        headers = self.xml.findall('{%s}header' % self.namespace)
        for header in headers:
            name = header.attrib.get('name', '')
            value = header.text
            if name in result:
                if not isinstance(result[name], set):
                    result[name] = [result[name]]
                else:
                    result[name] = []
                result[name].add(value)
            else:
                result[name] = value
        return result

    def set_headers(self, values):
        self.del_headers()
        for name in values:
            vals = values[name]
            if not isinstance(vals, (list, set)):
                vals = [values[name]]
            for value in vals:
                header = ET.Element('{%s}header' % self.namespace)
                header.attrib['name'] = name
                header.text = value
                self.xml.append(header)

    def del_headers(self):
        headers = self.xml.findall('{%s}header' % self.namespace)
        for header in headers:
            self.xml.remove(header)
