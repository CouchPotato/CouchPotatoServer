"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import hmac
import hashlib
import urllib
import base64

from sleekxmpp.xmlstream import ET, ElementBase, JID


class OAuth(ElementBase):

    name = 'oauth'
    namespace = 'urn:xmpp:oauth:0'
    plugin_attrib = 'oauth'
    interfaces = set(['oauth_consumer_key', 'oauth_nonce', 'oauth_signature',
                      'oauth_signature_method', 'oauth_timestamp',
                      'oauth_token', 'oauth_version'])
    sub_interfaces = interfaces

    def generate_signature(self, stanza, sfrom, sto, consumer_secret,
                                 token_secret, method='HMAC-SHA1'):
        self['oauth_signature_method'] = method

        request = urllib.quote('%s&%s' % (sfrom, sto), '')
        parameters = urllib.quote('&'.join([
            'oauth_consumer_key=%s' % self['oauth_consumer_key'],
            'oauth_nonce=%s' % self['oauth_nonce'],
            'oauth_signature_method=%s' % self['oauth_signature_method'],
            'oauth_timestamp=%s' % self['oauth_timestamp'],
            'oauth_token=%s' % self['oauth_token'],
            'oauth_version=%s' % self['oauth_version']
        ]), '')

        sigbase = '%s&%s&%s' % (stanza, request, parameters)

        consumer_secret = urllib.quote(consumer_secret, '')
        token_secret = urllib.quote(token_secret, '')
        key = '%s&%s' % (consumer_secret, token_secret)

        if method == 'HMAC-SHA1':
            sig = base64.b64encode(hmac.new(key, sigbase, hashlib.sha1).digest())
        elif method == 'PLAINTEXT':
            sig = key

        self['oauth_signature'] = sig
        return sig

    def verify_signature(self, stanza, sfrom, sto, consumer_secret,
                               token_secret):
        method = self['oauth_signature_method']

        request = urllib.quote('%s&%s' % (sfrom, sto), '')
        parameters = urllib.quote('&'.join([
            'oauth_consumer_key=%s' % self['oauth_consumer_key'],
            'oauth_nonce=%s' % self['oauth_nonce'],
            'oauth_signature_method=%s' % self['oauth_signature_method'],
            'oauth_timestamp=%s' % self['oauth_timestamp'],
            'oauth_token=%s' % self['oauth_token'],
            'oauth_version=%s' % self['oauth_version']
        ]), '')

        sigbase = '%s&%s&%s' % (stanza, request, parameters)

        consumer_secret = urllib.quote(consumer_secret, '')
        token_secret = urllib.quote(token_secret, '')
        key = '%s&%s' % (consumer_secret, token_secret)

        if method == 'HMAC-SHA1':
            sig = base64.b64encode(hmac.new(key, sigbase, hashlib.sha1).digest())
        elif method == 'PLAINTEXT':
            sig = key

        return self['oauth_signature'] == sig
