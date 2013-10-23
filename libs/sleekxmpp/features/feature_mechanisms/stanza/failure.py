"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import StanzaBase, ET


class Failure(StanzaBase):

    """
    """

    name = 'failure'
    namespace = 'urn:ietf:params:xml:ns:xmpp-sasl'
    interfaces = set(('condition', 'text'))
    plugin_attrib = name
    sub_interfaces = set(('text',))
    conditions = set(('aborted', 'account-disabled', 'credentials-expired',
        'encryption-required', 'incorrect-encoding', 'invalid-authzid',
        'invalid-mechanism', 'malformed-request', 'mechansism-too-weak',
        'not-authorized', 'temporary-auth-failure'))

    def setup(self, xml=None):
        """
        Populate the stanza object using an optional XML object.

        Overrides ElementBase.setup.

        Sets a default error type and condition, and changes the
        parent stanza's type to 'error'.

        Arguments:
            xml -- Use an existing XML object for the stanza's values.
        """
        # StanzaBase overrides self.namespace
        self.namespace = Failure.namespace

        if StanzaBase.setup(self, xml):
            #If we had to generate XML then set default values.
            self['condition'] = 'not-authorized'

        self.xml.tag = self.tag_name()

    def get_condition(self):
        """Return the condition element's name."""
        for child in self.xml:
            if "{%s}" % self.namespace in child.tag:
                cond = child.tag.split('}', 1)[-1]
                if cond in self.conditions:
                    return cond
        return 'not-authorized'

    def set_condition(self, value):
        """
        Set the tag name of the condition element.

        Arguments:
           value -- The tag name of the condition element.
        """
        if value in self.conditions:
            del self['condition']
            self.xml.append(ET.Element("{%s}%s" % (self.namespace, value)))
        return self

    def del_condition(self):
        """Remove the condition element."""
        for child in self.xml:
            if "{%s}" % self.condition_ns in child.tag:
                tag = child.tag.split('}', 1)[-1]
                if tag in self.conditions:
                    self.xml.remove(child)
        return self
