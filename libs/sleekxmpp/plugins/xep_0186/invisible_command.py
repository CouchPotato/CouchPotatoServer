"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0186 import stanza, Visible, Invisible


log = logging.getLogger(__name__)


class XEP_0186(BasePlugin):

    name = 'xep_0186'
    description = 'XEP-0186: Invisible Command'
    dependencies = set(['xep_0030'])

    def plugin_init(self):
        register_stanza_plugin(Iq, Visible)
        register_stanza_plugin(Iq, Invisible)

    def set_invisible(self, ifrom=None, block=True, callback=None,
                            timeout=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq.enable('invisible')
        iq.send(block=block, callback=callback, timeout=timeout)

    def set_visible(self, ifrom=None, block=True, callback=None,
                          timeout=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq.enable('visible')
        iq.send(block=block, callback=callback, timeout=timeout)
