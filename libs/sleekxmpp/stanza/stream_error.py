"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza.error import Error
from sleekxmpp.xmlstream import StanzaBase


class StreamError(Error, StanzaBase):

    """
    XMPP stanzas of type 'error' should include an <error> stanza that
    describes the nature of the error and how it should be handled.

    Use the 'XEP-0086: Error Condition Mappings' plugin to include error
    codes used in older XMPP versions.

    The stream:error stanza is used to provide more information for
    error that occur with the underlying XML stream itself, and not
    a particular stanza.

    Note: The StreamError stanza is mostly the same as the normal
          Error stanza, but with different namespaces and
          condition names.

    Example error stanza:
        <stream:error>
          <not-well-formed xmlns="urn:ietf:params:xml:ns:xmpp-streams" />
          <text xmlns="urn:ietf:params:xml:ns:xmpp-streams">
            XML was not well-formed.
          </text>
        </stream:error>

    Stanza Interface:
        condition -- The name of the condition element.
        text      -- Human readable description of the error.

    Attributes:
        conditions   -- The set of allowable error condition elements.
        condition_ns -- The namespace for the condition element.

    Methods:
        setup         -- Overrides ElementBase.setup.
        get_condition -- Retrieve the name of the condition element.
        set_condition -- Add a condition element.
        del_condition -- Remove the condition element.
        get_text      -- Retrieve the contents of the <text> element.
        set_text      -- Set the contents of the <text> element.
        del_text      -- Remove the <text> element.
    """

    namespace = 'http://etherx.jabber.org/streams'
    interfaces = set(('condition', 'text', 'see_other_host'))
    conditions = set((
        'bad-format', 'bad-namespace-prefix', 'conflict',
        'connection-timeout', 'host-gone', 'host-unknown',
        'improper-addressing', 'internal-server-error', 'invalid-from',
        'invalid-namespace', 'invalid-xml', 'not-authorized',
        'not-well-formed', 'policy-violation', 'remote-connection-failed',
        'reset', 'resource-constraint', 'restricted-xml', 'see-other-host',
        'system-shutdown', 'undefined-condition', 'unsupported-encoding',
        'unsupported-feature', 'unsupported-stanza-type',
        'unsupported-version'))
    condition_ns = 'urn:ietf:params:xml:ns:xmpp-streams'

    def get_see_other_host(self):
        ns = self.condition_ns
        return self._get_sub_text('{%s}see-other-host' % ns, '')

    def set_see_other_host(self, value):
        if value:
            del self['condition']
            ns = self.condition_ns
            return self._set_sub_text('{%s}see-other-host' % ns, value)
        elif self['condition'] == 'see-other-host':
            del self['condition']

    def del_see_other_host(self):
        self._del_sub('{%s}see-other-host' % self.condition_ns)
