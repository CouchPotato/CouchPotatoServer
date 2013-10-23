"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Mechanisms(ElementBase):

    """
    """

    name = 'mechanisms'
    namespace = 'urn:ietf:params:xml:ns:xmpp-sasl'
    interfaces = set(('mechanisms', 'required'))
    plugin_attrib = name
    is_extension = True

    def get_required(self):
        """
        """
        return True

    def get_mechanisms(self):
        """
        """
        results = []
        mechs = self.findall('{%s}mechanism' % self.namespace)
        if mechs:
            for mech in mechs:
                results.append(mech.text)
        return results

    def set_mechanisms(self, values):
        """
        """
        self.del_mechanisms()
        for val in values:
            mech = ET.Element('{%s}mechanism' % self.namespace)
            mech.text = val
            self.append(mech)

    def del_mechanisms(self):
        """
        """
        mechs = self.findall('{%s}mechanism' % self.namespace)
        if mechs:
            for mech in mechs:
                self.xml.remove(mech)
