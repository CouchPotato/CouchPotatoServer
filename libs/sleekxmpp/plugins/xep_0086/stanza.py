"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Error
from sleekxmpp.xmlstream import ElementBase, ET, register_stanza_plugin


class LegacyError(ElementBase):

    """
    Older XMPP implementations used code based error messages, similar
    to HTTP response codes. Since then, error condition elements have
    been introduced. XEP-0086 provides a mapping between the new
    condition elements and a combination of error types and the older
    response codes.

    Also see <http://xmpp.org/extensions/xep-0086.html>.

    Example legacy error stanzas:
        <error xmlns="jabber:client" code="501" type="cancel">
          <feature-not-implemented
                xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" />
        </error>

        <error code="402" type="auth">
          <payment-required
                xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" />
        </error>

    Attributes:
        error_map -- A map of error conditions to error types and
                     code values.
    Methods:
        setup         -- Overrides ElementBase.setup
        set_condition -- Remap the type and code interfaces when a
                         condition is set.
    """

    name = 'legacy'
    namespace = Error.namespace
    plugin_attrib = name
    interfaces = set(('condition',))
    overrides = ['set_condition']

    error_map = {'bad-request': ('modify', '400'),
                 'conflict': ('cancel', '409'),
                 'feature-not-implemented': ('cancel', '501'),
                 'forbidden': ('auth', '403'),
                 'gone': ('modify', '302'),
                 'internal-server-error': ('wait', '500'),
                 'item-not-found': ('cancel', '404'),
                 'jid-malformed': ('modify', '400'),
                 'not-acceptable': ('modify', '406'),
                 'not-allowed': ('cancel', '405'),
                 'not-authorized': ('auth', '401'),
                 'payment-required': ('auth', '402'),
                 'recipient-unavailable': ('wait', '404'),
                 'redirect': ('modify', '302'),
                 'registration-required': ('auth', '407'),
                 'remote-server-not-found': ('cancel', '404'),
                 'remote-server-timeout': ('wait', '504'),
                 'resource-constraint': ('wait', '500'),
                 'service-unavailable': ('cancel', '503'),
                 'subscription-required': ('auth', '407'),
                 'undefined-condition': (None, '500'),
                 'unexpected-request': ('wait', '400')}

    def setup(self, xml):
        """Don't create XML for the plugin."""
        self.xml = ET.Element('')

    def set_condition(self, value):
        """
        Set the error type and code based on the given error
        condition value.

        Arguments:
            value -- The new error condition.
        """
        self.parent().set_condition(value)

        error_data = self.error_map.get(value, None)
        if error_data is not None:
            if error_data[0] is not None:
                self.parent()['type'] = error_data[0]
            self.parent()['code'] = error_data[1]
