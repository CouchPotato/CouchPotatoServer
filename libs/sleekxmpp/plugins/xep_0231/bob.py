"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz,
                       Emmanuel Gil Peyrot <linkmauve@linkmauve.fr>
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging
import hashlib

from sleekxmpp.stanza import Iq
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.base import BasePlugin
from sleekxmpp.plugins.xep_0231 import stanza, BitsOfBinary


log = logging.getLogger(__name__)


class XEP_0231(BasePlugin):

    """
    XEP-0231 Bits of Binary
    """

    name = 'xep_0231'
    description = 'XEP-0231: Bits of Binary'
    dependencies = set(['xep_0030'])

    def plugin_init(self):
        self._cids = {}

        register_stanza_plugin(Iq, BitsOfBinary)

        self.xmpp.register_handler(
            Callback('Bits of Binary - Iq',
                StanzaPath('iq/bob'),
                self._handle_bob_iq))

        self.xmpp.register_handler(
            Callback('Bits of Binary - Message',
                StanzaPath('message/bob'),
                self._handle_bob))

        self.xmpp.register_handler(
            Callback('Bits of Binary - Presence',
                StanzaPath('presence/bob'),
                self._handle_bob))

        self.api.register(self._get_bob, 'get_bob', default=True)
        self.api.register(self._set_bob, 'set_bob', default=True)
        self.api.register(self._del_bob, 'del_bob', default=True)

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature='urn:xmpp:bob')
        self.xmpp.remove_handler('Bits of Binary - Iq')
        self.xmpp.remove_handler('Bits of Binary - Message')
        self.xmpp.remove_handler('Bits of Binary - Presence')

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('urn:xmpp:bob')

    def set_bob(self, data, mtype, cid=None, max_age=None):
        if cid is None:
            cid = 'sha1+%s@bob.xmpp.org' % hashlib.sha1(data).hexdigest()

        bob = BitsOfBinary()
        bob['data'] = data
        bob['type'] = mtype
        bob['cid'] = cid
        bob['max_age'] = max_age

        self.api['set_bob'](args=bob)

        return cid

    def get_bob(self, jid=None, cid=None, cached=True, ifrom=None,
                block=True, timeout=None, callback=None):
        if cached:
            data = self.api['get_bob'](None, None, ifrom, args=cid)
            if data is not None:
                if not isinstance(data, Iq):
                    iq = self.xmpp.Iq()
                    iq.append(data)
                    return iq
                return data

        iq = self.xmpp.Iq()
        iq['to'] = jid
        iq['from'] = ifrom
        iq['type'] = 'get'
        iq['bob']['cid'] = cid
        return iq.send(block=block, timeout=timeout, callback=callback)

    def del_bob(self, cid):
        self.api['del_bob'](args=cid)

    def _handle_bob_iq(self, iq):
        cid = iq['bob']['cid']

        if iq['type'] == 'result':
            self.api['set_bob'](iq['from'], None, iq['to'], args=iq['bob'])
            self.xmpp.event('bob', iq)
        elif iq['type'] == 'get':
            data = self.api['get_bob'](iq['to'], None, iq['from'], args=cid)
            if isinstance(data, Iq):
                data['id'] = iq['id']
                data.send()
                return

            iq.reply()
            iq.append(data)
            iq.send()

    def _handle_bob(self, stanza):
        self.api['set_bob'](stanza['from'], None,
                            stanza['to'], args=stanza['bob'])
        self.xmpp.event('bob', stanza)

    # =================================================================

    def _set_bob(self, jid, node, ifrom, bob):
        self._cids[bob['cid']] = bob

    def _get_bob(self, jid, node, ifrom, cid):
        if cid in self._cids:
            return self._cids[cid]
        else:
            raise XMPPError('item-not-found')

    def _del_bob(self, jid, node, ifrom, cid):
        if cid in self._cids:
            del self._cids[cid]
