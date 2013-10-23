"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.xmlstream import JID
from sleekxmpp.exceptions import IqError, IqTimeout


log = logging.getLogger(__name__)


class StaticCaps(object):

    """
    Extend the default StaticDisco implementation to provide
    support for extended identity information.
    """

    def __init__(self, xmpp, static):
        """
        Augment the default XEP-0030 static handler object.

        Arguments:
            static -- The default static XEP-0030 handler object.
        """
        self.xmpp = xmpp
        self.disco = self.xmpp['xep_0030']
        self.caps = self.xmpp['xep_0115']
        self.static = static
        self.ver_cache = {}
        self.jid_vers = {}

    def supports(self, jid, node, ifrom, data):
        """
        Check if a JID supports a given feature.

        The data parameter may provide:
            feature  -- The feature to check for support.
            local    -- If true, then the query is for a JID/node
                        combination handled by this Sleek instance and
                        no stanzas need to be sent.
                        Otherwise, a disco stanza must be sent to the
                        remove JID to retrieve the info.
            cached   -- If true, then look for the disco info data from
                        the local cache system. If no results are found,
                        send the query as usual. The self.use_cache
                        setting must be set to true for this option to
                        be useful. If set to false, then the cache will
                        be skipped, even if a result has already been
                        cached. Defaults to false.
        """
        feature = data.get('feature', None)

        data = {'local': data.get('local', False),
                'cached': data.get('cached', True)}

        if not feature:
            return False

        if node in (None, ''):
            info = self.caps.get_caps(jid)
            if info and feature in info['features']:
                return True

        try:
            info = self.disco.get_info(jid=jid, node=node,
                                       ifrom=ifrom, **data)
            info = self.disco._wrap(ifrom, jid, info, True)
            return feature in info['disco_info']['features']
        except IqError:
            return False
        except IqTimeout:
            return None

    def has_identity(self, jid, node, ifrom, data):
        """
        Check if a JID has a given identity.

        The data parameter may provide:
            category -- The category of the identity to check.
            itype    -- The type of the identity to check.
            lang     -- The language of the identity to check.
            local    -- If true, then the query is for a JID/node
                        combination handled by this Sleek instance and
                        no stanzas need to be sent.
                        Otherwise, a disco stanza must be sent to the
                        remove JID to retrieve the info.
            cached   -- If true, then look for the disco info data from
                        the local cache system. If no results are found,
                        send the query as usual. The self.use_cache
                        setting must be set to true for this option to
                        be useful. If set to false, then the cache will
                        be skipped, even if a result has already been
                        cached. Defaults to false.
        """
        identity = (data.get('category', None),
                    data.get('itype', None),
                    data.get('lang', None))

        data = {'local': data.get('local', False),
                'cached': data.get('cached', True)}

        trunc = lambda i: (i[0], i[1], i[2])

        if node in (None, ''):
            info = self.caps.get_caps(jid)
            if info and identity in map(trunc, info['identities']):
                return True

        try:
            info = self.disco.get_info(jid=jid, node=node,
                                       ifrom=ifrom, **data)
            info = self.disco._wrap(ifrom, jid, info, True)
            return identity in map(trunc, info['disco_info']['identities'])
        except IqError:
            return False
        except IqTimeout:
            return None

    def cache_caps(self, jid, node, ifrom, data):
        with self.static.lock:
            verstring = data.get('verstring', None)
            info = data.get('info', None)
            if not verstring or not info:
                return
            self.ver_cache[verstring] = info

    def assign_verstring(self, jid, node, ifrom, data):
        with self.static.lock:
            if isinstance(jid, JID):
                jid = jid.full
            self.jid_vers[jid] = data.get('verstring', None)

    def get_verstring(self, jid, node, ifrom, data):
        with self.static.lock:
            return self.jid_vers.get(jid, None)

    def get_caps(self, jid, node, ifrom, data):
        with self.static.lock:
            return self.ver_cache.get(data.get('verstring', None), None)
