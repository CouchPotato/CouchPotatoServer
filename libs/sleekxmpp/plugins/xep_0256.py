"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Presence
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.plugins import BasePlugin, register_plugin
from sleekxmpp.xmlstream import register_stanza_plugin

from sleekxmpp.plugins.xep_0012 import stanza, LastActivity


log = logging.getLogger(__name__)


class XEP_0256(BasePlugin):

    name = 'xep_0256'
    description = 'XEP-0256: Last Activity in Presence'
    dependencies = set(['xep_0012'])
    stanza = stanza
    default_config = {
        'auto_last_activity': False
    }

    def plugin_init(self):
        register_stanza_plugin(Presence, LastActivity)

        self.xmpp.add_filter('out', self._initial_presence_activity)
        self.xmpp.add_event_handler('connected', self._reset_presence_activity)

        self._initial_presence = set()

    def plugin_end(self):
        self.xmpp.del_filter('out', self._initial_presence_activity)
        self.xmpp.del_event_handler('connected', self._reset_presence_activity)

    def _reset_presence_activity(self, e):
        self._initial_presence = set()

    def _initial_presence_activity(self, stanza):
        if isinstance(stanza, Presence):
            use_last_activity = False

            if self.auto_last_activity and  stanza['show'] in ('xa', 'away'):
                use_last_activity = True

            if stanza['from'] not in self._initial_presence:
                self._initial_presence.add(stanza['from'])
                use_last_activity = True

            if use_last_activity:
                plugin = self.xmpp['xep_0012']
                try:
                    result = plugin.api['get_last_activity'](stanza['from'],
                                                             None,
                                                             stanza['to'])
                    seconds = result['last_activity']['seconds']
                except XMPPError:
                    seconds = None

                if seconds is not None:
                    stanza['last_activity']['seconds'] = seconds
        return stanza


register_plugin(XEP_0256)
