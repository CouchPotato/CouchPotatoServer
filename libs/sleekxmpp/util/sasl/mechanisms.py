# -*- coding: utf-8 -*-
"""
    sleekxmpp.util.sasl.mechanisms
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A collection of supported SASL mechanisms.

    This module was originally based on Dave Cridland's Suelta library.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2012 Nathanael C. Fritz, Lance J.T. Stout
    :license: MIT, see LICENSE for more details
"""

import sys
import hmac
import random

from base64 import b64encode, b64decode

from sleekxmpp.util import bytes, hash, XOR, quote, num_to_bytes
from sleekxmpp.util.sasl.client import sasl_mech, Mech, \
                                       SASLCancelled, SASLFailed


@sasl_mech(0)
class ANONYMOUS(Mech):

    name = 'ANONYMOUS'

    def process(self, challenge=b''):
        return b'Anonymous, Suelta'


@sasl_mech(1)
class LOGIN(Mech):

    name = 'LOGIN'
    required_credentials = set(['username', 'password'])

    def setup(self, name):
        self.step = 0

    def process(self, challenge=b''):
        if not challenge:
            return b''

        if self.step == 0:
            self.step = 1
            return self.credentials['username']
        else:
            return self.credentials['password']


@sasl_mech(2)
class PLAIN(Mech):

    name = 'PLAIN'
    required_credentials = set(['username', 'password'])
    optional_credentials = set(['authzid'])
    security = set(['encrypted', 'encrypted_plain', 'unencrypted_plain'])

    def setup(self, name):
        if not self.security_settings['encrypted']:
            if not self.security_settings['unencrypted_plain']:
                raise SASLCancelled('PLAIN without encryption')
        else:
            if not self.security_settings['encrypted_plain']:
                raise SASLCancelled('PLAIN with encryption')

    def process(self, challenge=b''):
        authzid = self.credentials['authzid']
        authcid = self.credentials['username']
        password = self.credentials['password']
        return authzid + b'\x00' + authcid + b'\x00' + password


@sasl_mech(100)
class EXTERNAL(Mech):

    name = 'EXTERNAL'
    optional_credentials = set(['authzid'])

    def process(self, challenge=b''):
        return self.credentials['authzid']


@sasl_mech(30)
class X_FACEBOOK_PLATFORM(Mech):

    name = 'X-FACEBOOK-PLATFORM'
    required_credentials = set(['api_key', 'access_token'])

    def process(self, challenge=b''):
        if challenge:
            values = {}
            for kv in challenge.split(b'&'):
                key, value = kv.split(b'=')
                values[key] = value

            resp_data = {
                b'method': values[b'method'],
                b'v': b'1.0',
                b'call_id': b'1.0',
                b'nonce': values[b'nonce'],
                b'access_token': self.credentials['access_token'],
                b'api_key': self.credentials['api_key']
            }

            resp = '&'.join(['%s=%s' % (k, v) for k, v in resp_data.items()])
            return bytes(resp)
        return b''


@sasl_mech(10)
class X_MESSENGER_OAUTH2(Mech):

    name = 'X-MESSENGER-OAUTH2'
    required_credentials = set(['access_token'])

    def process(self, challenge=b''):
        return self.credentials['access_token']


@sasl_mech(10)
class X_OAUTH2(Mech):

    name = 'X-OAUTH2'
    required_credentials = set(['username', 'access_token'])

    def process(self, challenge=b''):
        return b'\x00' + self.credentials['username'] + \
               b'\x00' + self.credentials['access_token']


@sasl_mech(3)
class X_GOOGLE_TOKEN(Mech):

    name = 'X-GOOGLE-TOKEN'
    required_credentials = set(['email', 'access_token'])

    def process(self, challenge=b''):
        email = self.credentials['email']
        token = self.credentials['access_token']
        return b'\x00' + email + b'\x00' + token


@sasl_mech(20)
class CRAM(Mech):

    name = 'CRAM'
    use_hashes = True
    required_credentials = set(['username', 'password'])
    security = set(['encrypted', 'unencrypted_cram'])

    def setup(self, name):
        self.hash_name = name[5:]
        self.hash = hash(self.hash_name)
        if self.hash is None:
            raise SASLCancelled('Unknown hash: %s' % self.hash_name)
        if not self.security_settings['encrypted']:
            if not self.security_settings['unencrypted_cram']:
                raise SASLCancelled('Unecrypted CRAM-%s' % self.hash_name)

    def process(self, challenge=b''):
        if not challenge:
            return None

        username = self.credentials['username']
        password = self.credentials['password']

        mac = hmac.HMAC(key=password, digestmod=self.hash)
        mac.update(challenge)

        return username + b' ' + bytes(mac.hexdigest())


@sasl_mech(60)
class SCRAM(Mech):

    name = 'SCRAM'
    use_hashes = True
    channel_binding = True
    required_credentials = set(['username', 'password'])
    optional_credentials = set(['authzid', 'channel_binding'])
    security = set(['encrypted', 'unencrypted_scram'])

    def setup(self, name):
        self.use_channel_binding = False
        if name[-5:] == '-PLUS':
            name = name[:-5]
            self.use_channel_binding = True

        self.hash_name = name[6:]
        self.hash = hash(self.hash_name)

        if self.hash is None:
            raise SASLCancelled('Unknown hash: %s' % self.hash_name)
        if not self.security_settings['encrypted']:
            if not self.security_settings['unencrypted_scram']:
                raise SASLCancelled('Unencrypted SCRAM')

        self.step = 0
        self._mutual_auth = False

    def HMAC(self, key, msg):
        return hmac.HMAC(key=key, msg=msg, digestmod=self.hash).digest()

    def Hi(self, text, salt, iterations):
        text = bytes(text)
        ui1 = self.HMAC(text, salt + b'\0\0\0\01')
        ui = ui1
        for i in range(iterations - 1):
            ui1 = self.HMAC(text, ui1)
            ui = XOR(ui, ui1)
        return ui

    def H(self, text):
        return self.hash(text).digest()

    def saslname(self, value):
        escaped = b''
        for char in bytes(value):
            if char == b',':
                escaped += b'=2C'
            elif char == b'=':
                escaped += b'=3D'
            else:
                if isinstance(char, int):
                    char = chr(char)
                escaped += bytes(char)
        return escaped

    def parse(self, challenge):
        items = {}
        for key, value in [item.split(b'=', 1) for item in challenge.split(b',')]:
            items[key] = value
        return items

    def process(self, challenge=b''):
        steps = [self.process_1, self.process_2, self.process_3]
        return steps[self.step](challenge)

    def process_1(self, challenge):
        self.step = 1
        data = {}

        self.cnonce = bytes(('%s' % random.random())[2:])

        gs2_cbind_flag = b'n'
        if self.credentials['channel_binding']:
            if self.use_channel_binding:
                gs2_cbind_flag = b'p=tls-unique'
            else:
                gs2_cbind_flag = b'y'

        authzid = b''
        if self.credentials['authzid']:
            authzid = b'a=' + self.saslname(self.credentials['authzid'])

        self.gs2_header = gs2_cbind_flag + b',' + authzid + b','

        nonce = b'r=' + self.cnonce
        username = b'n=' + self.saslname(self.credentials['username'])

        self.client_first_message_bare = username + b',' + nonce
        self.client_first_message = self.gs2_header + \
                                    self.client_first_message_bare

        return self.client_first_message

    def process_2(self, challenge):
        self.step = 2

        data = self.parse(challenge)
        if b'm' in data:
            raise SASLCancelled('Received reserved attribute.')

        salt = b64decode(data[b's'])
        iteration_count = int(data[b'i'])
        nonce = data[b'r']

        if nonce[:len(self.cnonce)] != self.cnonce:
            raise SASLCancelled('Invalid nonce')

        cbind_data = self.credentials['channel_binding']
        cbind_input = self.gs2_header + cbind_data
        channel_binding = b'c=' + b64encode(cbind_input).replace(b'\n', b'')

        client_final_message_without_proof = channel_binding + b',' + \
                                             b'r=' + nonce

        salted_password = self.Hi(self.credentials['password'],
                                       salt,
                                       iteration_count)
        client_key = self.HMAC(salted_password, b'Client Key')
        stored_key = self.H(client_key)
        auth_message = self.client_first_message_bare + b',' + \
                       challenge + b',' + \
                       client_final_message_without_proof
        client_signature = self.HMAC(stored_key, auth_message)
        client_proof = XOR(client_key, client_signature)
        server_key = self.HMAC(salted_password, b'Server Key')

        self.server_signature = self.HMAC(server_key, auth_message)

        client_final_message = client_final_message_without_proof + \
                               b',p=' + b64encode(client_proof)

        return client_final_message

    def process_3(self, challenge):
        data = self.parse(challenge)
        verifier = data.get(b'v', None)
        error = data.get(b'e', 'Unknown error')

        if not verifier:
            raise SASLFailed(error)

        if b64decode(verifier) != self.server_signature:
            raise SASLMutualAuthFailed()

        self._mutual_auth = True

        return b''


@sasl_mech(30)
class DIGEST(Mech):

    name = 'DIGEST'
    use_hashes = True
    required_credentials = set(['username', 'password', 'realm', 'service', 'host'])
    optional_credentials = set(['authzid', 'service-name'])
    security = set(['encrypted', 'unencrypted_digest'])

    def setup(self, name):
        self.hash_name = name[7:]
        self.hash = hash(self.hash_name)
        if self.hash is None:
            raise SASLCancelled('Unknown hash: %s' % self.hash_name)
        if not self.security_settings['encrypted']:
            if not self.security_settings['unencrypted_digest']:
                raise SASLCancelled('Unencrypted DIGEST')

        self.qops = [b'auth']
        self.qop = b'auth'
        self.maxbuf = b'65536'
        self.nonce = b''
        self.cnonce = b''
        self.nonce_count = 1

    def parse(self, challenge=b''):
        data = {}
        var_name = b''
        var_value = b''

        # States: var, new_var, end, quote, escaped_quote
        state = 'var'


        for char in challenge:
            if sys.version_info >= (3, 0):
                char = bytes([char])

            if state == 'var':
                if char.isspace():
                    continue
                if char == b'=':
                    state = 'value'
                else:
                    var_name += char
            elif state == 'value':
                if char == b'"':
                    state = 'quote'
                elif char == b',':
                    if var_name:
                        data[var_name.decode('utf-8')] = var_value
                    var_name = b''
                    var_value = b''
                    state = 'var'
                else:
                    var_value += char
            elif state == 'escaped':
                var_value += char
            elif state == 'quote':
                if char == b'\\':
                    state = 'escaped'
                elif char == b'"':
                    state = 'end'
                else:
                    var_value += char
            else:
                if char == b',':
                    if var_name:
                        data[var_name.decode('utf-8')] = var_value
                    var_name = b''
                    var_value = b''
                    state = 'var'
                else:
                    var_value += char

        if var_name:
            data[var_name.decode('utf-8')] = var_value
        var_name = b''
        var_value = b''
        state = 'var'
        return data

    def MAC(self, key, seq, msg):
        mac = hmac.HMAC(key=key, digestmod=self.hash)
        seqnum = num_to_bytes(seq)
        mac.update(seqnum)
        mac.update(msg)
        return mac.digest()[:10] + b'\x00\x01' + seqnum

    def A1(self):
        username = self.credentials['username']
        password = self.credentials['password']
        authzid = self.credentials['authzid']
        realm = self.credentials['realm']

        a1 = self.hash()
        a1.update(username + b':' + realm + b':' + password)
        a1 = a1.digest()
        a1 += b':' + self.nonce + b':' + self.cnonce
        if authzid:
            a1 += b':' + authzid

        return bytes(a1)

    def A2(self, prefix=b''):
        a2 = prefix + b':' + self.digest_uri()
        if self.qop in (b'auth-int', b'auth-conf'):
            a2 += b':00000000000000000000000000000000'
        return bytes(a2)

    def response(self, prefix=b''):
        nc = bytes('%08x' % self.nonce_count)

        a1 = bytes(self.hash(self.A1()).hexdigest().lower())
        a2 = bytes(self.hash(self.A2(prefix)).hexdigest().lower())
        s = self.nonce + b':' + nc + b':' + self.cnonce + \
                         b':' + self.qop + b':' + a2

        return bytes(self.hash(a1 + b':' + s).hexdigest().lower())

    def digest_uri(self):
        serv_type = self.credentials['service']
        serv_name = self.credentials['service-name']
        host = self.credentials['host']

        uri = serv_type + b'/' + host
        if serv_name and host != serv_name:
            uri += b'/' + serv_name
        return uri

    def respond(self):
        data = {
            'username': quote(self.credentials['username']),
            'authzid': quote(self.credentials['authzid']),
            'realm': quote(self.credentials['realm']),
            'nonce': quote(self.nonce),
            'cnonce': quote(self.cnonce),
            'nc': bytes('%08x' % self.nonce_count),
            'qop': self.qop,
            'digest-uri': quote(self.digest_uri()),
            'response': self.response(b'AUTHENTICATE'),
            'maxbuf': self.maxbuf
        }
        resp = b''
        for key, value in data.items():
            if value and value != b'""':
                resp += b',' + bytes(key) + b'=' + bytes(value)
        return resp[1:]

    def process(self, challenge=b''):
        if not challenge:
            if self.cnonce and self.nonce and self.nonce_count and self.qop:
                self.nonce_count += 1
                return self.respond()
            return b''

        data = self.parse(challenge)
        if 'rspauth' in data:
            if data['rspauth'] != self.response():
                raise SASLMutualAuthFailed()
        else:
            self.nonce_count = 1
            self.cnonce = bytes('%s' % random.random())[2:]
            self.qops = data.get('qop', [b'auth'])
            self.qop = b'auth'
            if 'nonce' in data:
                self.nonce = data['nonce']
            if 'realm' in data and not self.credentials['realm']:
                self.credentials['realm'] = data['realm']

            return self.respond()


try:
    import kerberos
except ImportError:
    pass
else:
    @sasl_mech(75)
    class GSSAPI(Mech):

        name = 'GSSAPI'
        required_credentials = set(['username', 'service-name'])
        optional_credentials = set(['authzid'])

        def setup(self, name):
            authzid = self.credentials['authzid']
            if not authzid:
                authzid = 'xmpp@%s' % self.credentials['service-name']

            _, self.gss = kerberos.authGSSClientInit(authzid)
            self.step = 0

        def process(self, challenge=b''):
            b64_challenge = b64encode(challenge)
            try:
                if self.step == 0:
                    result = kerberos.authGSSClientStep(self.gss, b64_challenge)
                    if result != kerberos.AUTH_GSS_CONTINUE:
                        self.step = 1
                elif self.step == 1:
                    username = self.credentials['username']

                    kerberos.authGSSClientUnwrap(self.gss, b64_challenge)
                    resp = kerberos.authGSSClientResponse(self.gss)
                    kerberos.authGSSClientWrap(self.gss, resp, username)

                resp = kerberos.authGSSClientResponse(self.gss)
            except kerberos.GSSError as e:
                raise SASLCancelled('Kerberos error: %s' % e.message)
            if not resp:
                return b''
            else:
                return b64decode(resp)
