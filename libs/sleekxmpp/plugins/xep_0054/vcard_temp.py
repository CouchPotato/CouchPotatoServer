"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp import Iq
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0054 import VCardTemp, stanza


log = logging.getLogger(__name__)


class XEP_0054(BasePlugin):

    """
    XEP-0054: vcard-temp
    """

    name = 'xep_0054'
    description = 'XEP-0054: vcard-temp'
    dependencies = set(['xep_0030', 'xep_0082'])
    stanza = stanza

    def plugin_init(self):
        """
        Start the XEP-0054 plugin.
        """
        register_stanza_plugin(Iq, VCardTemp)


        self.api.register(self._set_vcard, 'set_vcard', default=True)
        self.api.register(self._get_vcard, 'get_vcard', default=True)
        self.api.register(self._del_vcard, 'del_vcard', default=True)

        self._vcard_cache = {}

        self.xmpp.register_handler(
                Callback('VCardTemp',
                    StanzaPath('iq/vcard_temp'),
                    self._handle_get_vcard))

    def plugin_end(self):
        self.xmpp.remove_handler('VCardTemp')
        self.xmpp['xep_0030'].del_feature(feature='vcard-temp')

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('vcard-temp')

    def make_vcard(self):
        return VCardTemp()

    def get_vcard(self, jid=None, ifrom=None, local=False, cached=False,
                  block=True, callback=None, timeout=None):
        if self.xmpp.is_component and jid.domain == self.xmpp.boundjid.domain:
            local = True

        if local:
            vcard = self.api['get_vcard'](jid, None, ifrom)
            if not isinstance(vcard, Iq):
                iq = self.xmpp.Iq()
                if vcard is None:
                    vcard = VCardTemp()
                iq.append(vcard)
                return iq
            return vcard

        if cached:
            vcard = self.api['get_vcard'](jid, None, ifrom)
            if vcard is not None:
                if not isinstance(vcard, Iq):
                    iq = self.xmpp.Iq()
                    iq.append(vcard)
                    return iq
                return vcard

        iq = self.xmpp.Iq()
        iq['to'] = jid
        iq['from'] = ifrom
        iq['type'] = 'get'
        iq.enable('vcard_temp')

        vcard = iq.send(block=block, callback=callback, timeout=timeout)

        if block:
            self.api['set_vcard'](vcard['from'], args=vcard['vcard_temp'])
            return vcard

    def publish_vcard(self, vcard=None, jid=None, block=True, ifrom=None,
                      callback=None, timeout=None):
        self.api['set_vcard'](jid, None, ifrom, vcard)
        if self.xmpp.is_component:
            return

        iq = self.xmpp.Iq()
        iq['to'] = jid
        iq['from'] = ifrom
        iq['type'] = 'set'
        iq.append(vcard)
        return iq.send(block=block, callback=callback, timeout=timeout)

    def _handle_get_vcard(self, iq):
        if iq['type'] == 'result':
            self.api['set_vcard'](jid=iq['from'], args=iq['vcard_temp'])
            return
        elif iq['type'] == 'get':
            vcard = self.api['get_vcard'](iq['from'].bare)
            if isinstance(vcard, Iq):
                vcard.send()
            else:
                iq.reply()
                iq.append(vcard)
                iq.send()
        elif iq['type'] == 'set':
            raise XMPPError('service-unavailable')

    # =================================================================

    def _set_vcard(self, jid, node, ifrom, vcard):
        self._vcard_cache[jid.bare] = vcard

    def _get_vcard(self, jid, node, ifrom, vcard):
        return self._vcard_cache.get(jid.bare, None)

    def _del_vcard(self, jid, node, ifrom, vcard):
        if jid.bare in self._vcard_cache:
            del self._vcard_cache[jid.bare]
