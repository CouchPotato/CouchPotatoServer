"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase, ET


class Error(ElementBase):

    """
    XMPP stanzas of type 'error' should include an <error> stanza that
    describes the nature of the error and how it should be handled.

    Use the 'XEP-0086: Error Condition Mappings' plugin to include error
    codes used in older XMPP versions.

    Example error stanza:
        <error type="cancel" code="404">
          <item-not-found xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" />
          <text xmlns="urn:ietf:params:xml:ns:xmpp-stanzas">
            The item was not found.
          </text>
        </error>

    Stanza Interface:
        code      -- The error code used in older XMPP versions.
        condition -- The name of the condition element.
        text      -- Human readable description of the error.
        type      -- Error type indicating how the error should be handled.

    Attributes:
        conditions   -- The set of allowable error condition elements.
        condition_ns -- The namespace for the condition element.
        types        -- A set of values indicating how the error
                        should be treated.

    Methods:
        setup         -- Overrides ElementBase.setup.
        get_condition -- Retrieve the name of the condition element.
        set_condition -- Add a condition element.
        del_condition -- Remove the condition element.
        get_text      -- Retrieve the contents of the <text> element.
        set_text      -- Set the contents of the <text> element.
        del_text      -- Remove the <text> element.
    """

    namespace = 'jabber:client'
    name = 'error'
    plugin_attrib = 'error'
    interfaces = set(('code', 'condition', 'text', 'type',
                      'gone', 'redirect', 'by'))
    sub_interfaces = set(('text',))
    plugin_attrib_map = {}
    plugin_tag_map = {}
    conditions = set(('bad-request', 'conflict', 'feature-not-implemented',
                      'forbidden', 'gone', 'internal-server-error',
                      'item-not-found', 'jid-malformed', 'not-acceptable',
                      'not-allowed', 'not-authorized', 'payment-required',
                      'recipient-unavailable', 'redirect',
                      'registration-required', 'remote-server-not-found',
                      'remote-server-timeout', 'resource-constraint',
                      'service-unavailable', 'subscription-required',
                      'undefined-condition', 'unexpected-request'))
    condition_ns = 'urn:ietf:params:xml:ns:xmpp-stanzas'
    types = set(('cancel', 'continue', 'modify', 'auth', 'wait'))

    def setup(self, xml=None):
        """
        Populate the stanza object using an optional XML object.

        Overrides ElementBase.setup.

        Sets a default error type and condition, and changes the
        parent stanza's type to 'error'.

        Arguments:
            xml -- Use an existing XML object for the stanza's values.
        """
        if ElementBase.setup(self, xml):
            #If we had to generate XML then set default values.
            self['type'] = 'cancel'
            self['condition'] = 'feature-not-implemented'
        if self.parent is not None:
            self.parent()['type'] = 'error'

    def get_condition(self):
        """Return the condition element's name."""
        for child in self.xml:
            if "{%s}" % self.condition_ns in child.tag:
                cond = child.tag.split('}', 1)[-1]
                if cond in self.conditions:
                    return cond
        return ''

    def set_condition(self, value):
        """
        Set the tag name of the condition element.

        Arguments:
           value -- The tag name of the condition element.
        """
        if value in self.conditions:
            del self['condition']
            self.xml.append(ET.Element("{%s}%s" % (self.condition_ns, value)))
        return self

    def del_condition(self):
        """Remove the condition element."""
        for child in self.xml:
            if "{%s}" % self.condition_ns in child.tag:
                tag = child.tag.split('}', 1)[-1]
                if tag in self.conditions:
                    self.xml.remove(child)
        return self

    def get_text(self):
        """Retrieve the contents of the <text> element."""
        return self._get_sub_text('{%s}text' % self.condition_ns)

    def set_text(self, value):
        """
        Set the contents of the <text> element.

        Arguments:
            value -- The new contents for the <text> element.
        """
        self._set_sub_text('{%s}text' % self.condition_ns, text=value)
        return self

    def del_text(self):
        """Remove the <text> element."""
        self._del_sub('{%s}text' % self.condition_ns)
        return self

    def get_gone(self):
        return self._get_sub_text('{%s}gone' % self.condition_ns, '')

    def get_redirect(self):
        return self._get_sub_text('{%s}redirect' % self.condition_ns, '')

    def set_gone(self, value):
        if value:
            del self['condition']
            return self._set_sub_text('{%s}gone' % self.condition_ns, value)
        elif self['condition'] == 'gone':
            del self['condition']

    def set_redirect(self, value):
        if value:
            del self['condition']
            ns = self.condition_ns
            return self._set_sub_text('{%s}redirect' % ns, value)
        elif self['condition'] == 'redirect':
            del self['condition']

    def del_gone(self):
        self._del_sub('{%s}gone' % self.condition_ns)

    def del_redirect(self):
        self._del_sub('{%s}redirect' % self.condition_ns)


# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
Error.getCondition = Error.get_condition
Error.setCondition = Error.set_condition
Error.delCondition = Error.del_condition
Error.getText = Error.get_text
Error.setText = Error.set_text
Error.delText = Error.del_text
