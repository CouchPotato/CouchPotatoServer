# -*- coding: utf-8 -*-
"""
    sleekxmpp.util.sasl.client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    This module was originally based on Dave Cridland's Suelta library.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2012 Nathanael C. Fritz, Lance J.T. Stout
    :license: MIT, see LICENSE for more details
"""

import logging
import stringprep

from sleekxmpp.util import hashes, bytes, stringprep_profiles


log = logging.getLogger(__name__)


#: Global registry mapping mechanism names to implementation classes.
MECHANISMS = {}


#: Global registry mapping mechanism names to security scores.
MECH_SEC_SCORES = {}


#: The SASLprep profile of stringprep used to validate simple username
#: and password credentials.
saslprep = stringprep_profiles.create(
    nfkc=True,
    bidi=True,
    mappings=[
        stringprep_profiles.b1_mapping,
        stringprep_profiles.c12_mapping],
    prohibited=[
        stringprep.in_table_c12,
        stringprep.in_table_c21,
        stringprep.in_table_c22,
        stringprep.in_table_c3,
        stringprep.in_table_c4,
        stringprep.in_table_c5,
        stringprep.in_table_c6,
        stringprep.in_table_c7,
        stringprep.in_table_c8,
        stringprep.in_table_c9],
    unassigned=[stringprep.in_table_a1])


def sasl_mech(score):
    sec_score = score
    def register(mech):
        n = 0
        mech.score = sec_score
        if mech.use_hashes:
            for hashing_alg in hashes():
                n += 1
                score = mech.score + n
                name = '%s-%s' % (mech.name, hashing_alg)
                MECHANISMS[name] = mech
                MECH_SEC_SCORES[name] = score

                if mech.channel_binding:
                    name += '-PLUS'
                    score += 10
                    MECHANISMS[name] = mech
                    MECH_SEC_SCORES[name] = score
        else:
            MECHANISMS[mech.name] = mech
            MECH_SEC_SCORES[mech.name] = mech.score
            if mech.channel_binding:
                MECHANISMS[mech.name + '-PLUS'] = mech
                MECH_SEC_SCORES[name] = mech.score + 10
        return mech
    return register


class SASLNoAppropriateMechanism(Exception):
    def __init__(self, value=''):
        self.message = value


class SASLCancelled(Exception):
    def __init__(self, value=''):
        self.message = value


class SASLFailed(Exception):
    def __init__(self, value=''):
        self.message = value


class SASLMutualAuthFailed(SASLFailed):
    def __init__(self, value=''):
        self.message = value


class Mech(object):

    name = 'GENERIC'
    score = -1
    use_hashes = False
    channel_binding = False
    required_credentials = set()
    optional_credentials = set()
    security = set()

    def __init__(self, name, credentials, security_settings):
        self.credentials = credentials
        self.security_settings = security_settings
        self.values = {}
        self.base_name = self.name
        self.name = name
        self.setup(name)

    def setup(self, name):
        pass

    def process(self, challenge=b''):
        return b''


def choose(mech_list, credentials, security_settings, limit=None, min_mech=None):
    available_mechs = set(MECHANISMS.keys())
    if limit is None:
        limit = set(mech_list)
    if not isinstance(limit, set):
        limit = set(limit)
    if not isinstance(mech_list, set):
        mech_list = set(mech_list)

    mech_list = mech_list.intersection(limit)
    available_mechs = available_mechs.intersection(mech_list)

    best_score = MECH_SEC_SCORES.get(min_mech, -1)
    best_mech = None
    for name in available_mechs:
        if name in MECH_SEC_SCORES:
            if MECH_SEC_SCORES[name] > best_score:
                best_score = MECH_SEC_SCORES[name]
                best_mech = name
    if best_mech is None:
        raise SASLNoAppropriateMechanism()

    mech_class = MECHANISMS[best_mech]

    try:
        creds = credentials(mech_class.required_credentials,
                            mech_class.optional_credentials)
        for req in mech_class.required_credentials:
            if req not in creds:
                raise SASLCancelled('Missing credential: %s' % req)
        for opt in mech_class.optional_credentials:
            if opt not in creds:
                creds[opt] = b''
        for cred in creds:
            if cred in ('username', 'password', 'authzid'):
                creds[cred] = bytes(saslprep(creds[cred]))
            else:
                creds[cred] = bytes(creds[cred])
        security_opts = security_settings(mech_class.security)

        return mech_class(best_mech, creds, security_opts)
    except SASLCancelled as e:
        log.info('SASL: %s: %s', best_mech, e.message)
        mech_list.remove(best_mech)
        return choose(mech_list, credentials, security_settings,
                limit=limit,
                min_mech=min_mech)
