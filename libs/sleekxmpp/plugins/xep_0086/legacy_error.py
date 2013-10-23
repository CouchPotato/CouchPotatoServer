"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Error
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0086 import stanza, LegacyError


class XEP_0086(BasePlugin):

    """
    XEP-0086: Error Condition Mappings

    Older XMPP implementations used code based error messages, similar
    to HTTP response codes. Since then, error condition elements have
    been introduced. XEP-0086 provides a mapping between the new
    condition elements and a combination of error types and the older
    response codes.

    Also see <http://xmpp.org/extensions/xep-0086.html>.

    Configuration Values:
        override -- Indicates if applying legacy error codes should
                    be done automatically. Defaults to True.
                    If False, then inserting legacy error codes can
                    be done using:
                        iq['error']['legacy']['condition'] = ...
    """

    name = 'xep_0086'
    description = 'XEP-0086: Error Condition Mappings'
    dependencies = set()
    stanza = stanza
    default_config = {
        'override': True
    }

    def plugin_init(self):
        register_stanza_plugin(Error, LegacyError,
                               overrides=self.override)
