"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.thirdparty import GPG

from sleekxmpp.stanza import Presence, Message
from sleekxmpp.plugins.base import BasePlugin, register_plugin
from sleekxmpp.xmlstream import ElementBase, register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins.xep_0027 import stanza, Signed, Encrypted


def _extract_data(data, kind):
    stripped = []
    begin_headers = False
    begin_data = False
    for line in data.split('\n'):
        if not begin_headers and 'BEGIN PGP %s' % kind in line:
            begin_headers = True
            continue
        if begin_headers and line.stripped() == '':
            begin_data = True
            continue
        if 'END PGP %s' % kind in line:
            return '\n'.join(stripped)
        if begin_data:
            stripped.append(line)
    return ''


class XEP_0027(BasePlugin):

    name = 'xep_0027'
    description = 'XEP-0027: Current Jabber OpenPGP Usage'
    dependencies = set()
    stanza = stanza
    default_config = {
        'gpg_binary': 'gpg',
        'gpg_home': '',
        'use_agent': True,
        'keyring': None,
        'key_server': 'pgp.mit.edu'
    }

    def plugin_init(self):
        self.gpg = GPG(gnupghome=self.gpg_home,
                       gpgbinary=self.gpg_binary,
                       use_agent=self.use_agent,
                       keyring=self.keyring)

        self.xmpp.add_filter('out', self._sign_presence)

        self._keyids = {}

        self.api.register(self._set_keyid, 'set_keyid', default=True)
        self.api.register(self._get_keyid, 'get_keyid', default=True)
        self.api.register(self._del_keyid, 'del_keyid', default=True)
        self.api.register(self._get_keyids, 'get_keyids', default=True)

        register_stanza_plugin(Presence, Signed)
        register_stanza_plugin(Message, Encrypted)

        self.xmpp.add_event_handler('unverified_signed_presence',
                self._handle_unverified_signed_presence,
                threaded=True)

        self.xmpp.register_handler(
                Callback('Signed Presence',
                    StanzaPath('presence/signed'),
                    self._handle_signed_presence))

        self.xmpp.register_handler(
                Callback('Encrypted Message',
                    StanzaPath('message/encrypted'),
                    self._handle_encrypted_message))

    def plugin_end(self):
        self.xmpp.remove_handler('Encrypted Message')
        self.xmpp.remove_handler('Signed Presence')
        self.xmpp.del_filter('out', self._sign_presence)
        self.xmpp.del_event_handler('unverified_signed_presence',
                self._handle_unverified_signed_presence)

    def _sign_presence(self, stanza):
        if isinstance(stanza, Presence):
            if stanza['type'] == 'available' or \
                    stanza['type'] in Presence.showtypes:
                stanza['signed'] = stanza['status']
        return stanza

    def sign(self, data, jid=None):
        keyid = self.get_keyid(jid)
        if keyid:
            signed = self.gpg.sign(data, keyid=keyid)
            return _extract_data(signed.data, 'SIGNATURE')

    def encrypt(self, data, jid=None):
        keyid = self.get_keyid(jid)
        if keyid:
            enc = self.gpg.encrypt(data, keyid)
            return _extract_data(enc.data, 'MESSAGE')

    def decrypt(self, data, jid=None):
        template = '-----BEGIN PGP MESSAGE-----\n' + \
                   '\n' + \
                   '%s\n' + \
                   '-----END PGP MESSAGE-----\n'
        dec = self.gpg.decrypt(template % data)
        return dec.data

    def verify(self, data, sig, jid=None):
        template = '-----BEGIN PGP SIGNED MESSAGE-----\n' + \
                   'Hash: SHA1\n' + \
                   '\n' + \
                   '%s\n' + \
                   '-----BEGIN PGP SIGNATURE-----\n' + \
                   '\n' + \
                   '%s\n' + \
                   '-----END PGP SIGNATURE-----\n'
        v = self.gpg.verify(template % (data, sig))
        return v

    def set_keyid(self, jid=None, keyid=None):
        self.api['set_keyid'](jid, args=keyid)

    def get_keyid(self, jid=None):
        return self.api['get_keyid'](jid)

    def del_keyid(self, jid=None):
        self.api['del_keyid'](jid)

    def get_keyids(self):
        return self.api['get_keyids']()

    def _handle_signed_presence(self, pres):
        self.xmpp.event('unverified_signed_presence', pres)

    def _handle_unverified_signed_presence(self, pres):
        verified = self.verify(pres['status'], pres['signed'])
        if verified.key_id:
            if not self.get_keyid(pres['from']):
                known_keyids = [e['keyid'] for e in self.gpg.list_keys()]
                if verified.key_id not in known_keyids:
                    self.gpg.recv_keys(self.key_server, verified.key_id)
                self.set_keyid(jid=pres['from'], keyid=verified.key_id)
            self.xmpp.event('signed_presence', pres)

    def _handle_encrypted_message(self, msg):
        self.xmpp.event('encrypted_message', msg)

    # =================================================================

    def _set_keyid(self, jid, node, ifrom, keyid):
        self._keyids[jid] = keyid

    def _get_keyid(self, jid, node, ifrom, keyid):
        return self._keyids.get(jid, None)

    def _del_keyid(self, jid, node, ifrom, keyid):
        if jid in self._keyids:
            del self._keyids[jid]

    def _get_keyids(self, jid, node, ifrom, data):
        return self._keyids
