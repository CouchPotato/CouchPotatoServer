"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging
import threading

from sleekxmpp import Iq
from sleekxmpp.exceptions import XMPPError, IqError, IqTimeout
from sleekxmpp.xmlstream import JID
from sleekxmpp.plugins.xep_0030 import DiscoInfo, DiscoItems


log = logging.getLogger(__name__)


class StaticDisco(object):

    """
    While components will likely require fully dynamic handling
    of service discovery information, most clients and simple bots
    only need to manage a few disco nodes that will remain mostly
    static.

    StaticDisco provides a set of node handlers that will store
    static sets of disco info and items in memory.

    Attributes:
        nodes -- A dictionary mapping (JID, node) tuples to a dict
                 containing a disco#info and a disco#items stanza.
        xmpp  -- The main SleekXMPP object.
    """

    def __init__(self, xmpp, disco):
        """
        Create a static disco interface. Sets of disco#info and
        disco#items are maintained for every given JID and node
        combination. These stanzas are used to store disco
        information in memory without any additional processing.

        Arguments:
            xmpp -- The main SleekXMPP object.
        """
        self.nodes = {}
        self.xmpp = xmpp
        self.disco = disco
        self.lock = threading.RLock()

    def add_node(self, jid=None, node=None, ifrom=None):
        """
        Create a new set of stanzas for the provided
        JID and node combination.

        Arguments:
            jid  -- The JID that will own the new stanzas.
            node -- The node that will own the new stanzas.
        """
        with self.lock:
            if jid is None:
                jid = self.xmpp.boundjid.full
            if node is None:
                node = ''
            if ifrom is None:
                ifrom = ''
            if isinstance(ifrom, JID):
                ifrom = ifrom.full
            if (jid, node, ifrom) not in self.nodes:
                self.nodes[(jid, node, ifrom)] = {'info': DiscoInfo(),
                                           'items': DiscoItems()}
                self.nodes[(jid, node, ifrom)]['info']['node'] = node
                self.nodes[(jid, node, ifrom)]['items']['node'] = node

    def get_node(self, jid=None, node=None, ifrom=None):
        with self.lock:
            if jid is None:
                jid = self.xmpp.boundjid.full
            if node is None:
                node = ''
            if ifrom is None:
                ifrom = ''
            if isinstance(ifrom, JID):
                ifrom = ifrom.full
            if (jid, node, ifrom) not in self.nodes:
                self.add_node(jid, node, ifrom)
            return self.nodes[(jid, node, ifrom)]

    def node_exists(self, jid=None, node=None, ifrom=None):
        with self.lock:
            if jid is None:
                jid = self.xmpp.boundjid.full
            if node is None:
                node = ''
            if ifrom is None:
                ifrom = ''
            if isinstance(ifrom, JID):
                ifrom = ifrom.full
            if (jid, node, ifrom) not in self.nodes:
                return False
            return True

    # =================================================================
    # Node Handlers
    #
    # Each handler accepts four arguments: jid, node, ifrom, and data.
    # The jid and node parameters together determine the set of info
    # and items stanzas that will be retrieved or added. Additionally,
    # the ifrom value allows for cached results when results vary based
    # on the requester's JID. The data parameter is a dictionary with
    # additional parameters that will be passed to other calls.
    #
    # This implementation does not allow different responses based on
    # the requester's JID, except for cached results. To do that,
    # register a custom node handler.

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

        try:
            info = self.disco.get_info(jid=jid, node=node,
                                       ifrom=ifrom, **data)
            info = self.disco._wrap(ifrom, jid, info, True)
            features = info['disco_info']['features']
            return feature in features
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

        try:
            info = self.disco.get_info(jid=jid, node=node,
                                       ifrom=ifrom, **data)
            info = self.disco._wrap(ifrom, jid, info, True)
            trunc = lambda i: (i[0], i[1], i[2])
            return identity in map(trunc, info['disco_info']['identities'])
        except IqError:
            return False
        except IqTimeout:
            return None

    def get_info(self, jid, node, ifrom, data):
        """
        Return the stored info data for the requested JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if not self.node_exists(jid, node):
                if not node:
                    return DiscoInfo()
                else:
                    raise XMPPError(condition='item-not-found')
            else:
                return self.get_node(jid, node)['info']

    def set_info(self, jid, node, ifrom, data):
        """
        Set the entire info stanza for a JID/node at once.

        The data parameter is a disco#info substanza.
        """
        with self.lock:
            self.add_node(jid, node)
            self.get_node(jid, node)['info'] = data

    def del_info(self, jid, node, ifrom, data):
        """
        Reset the info stanza for a given JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if self.node_exists(jid, node):
                self.get_node(jid, node)['info'] = DiscoInfo()

    def get_items(self, jid, node, ifrom, data):
        """
        Return the stored items data for the requested JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if not self.node_exists(jid, node):
                if not node:
                    return DiscoItems()
                else:
                    raise XMPPError(condition='item-not-found')
            else:
                return self.get_node(jid, node)['items']

    def set_items(self, jid, node, ifrom, data):
        """
        Replace the stored items data for a JID/node combination.

        The data parameter may provide:
            items -- A set of items in tuple format.
        """
        with self.lock:
            items = data.get('items', set())
            self.add_node(jid, node)
            self.get_node(jid, node)['items']['items'] = items

    def del_items(self, jid, node, ifrom, data):
        """
        Reset the items stanza for a given JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if self.node_exists(jid, node):
                self.get_node(jid, node)['items'] = DiscoItems()

    def add_identity(self, jid, node, ifrom, data):
        """
        Add a new identity to te JID/node combination.

        The data parameter may provide:
            category -- The general category to which the agent belongs.
            itype    -- A more specific designation with the category.
            name     -- Optional human readable name for this identity.
            lang     -- Optional standard xml:lang value.
        """
        with self.lock:
            self.add_node(jid, node)
            self.get_node(jid, node)['info'].add_identity(
                    data.get('category', ''),
                    data.get('itype', ''),
                    data.get('name', None),
                    data.get('lang', None))

    def set_identities(self, jid, node, ifrom, data):
        """
        Add or replace all identities for a JID/node combination.

        The data parameter should include:
            identities -- A list of identities in tuple form:
                            (category, type, name, lang)
        """
        with self.lock:
            identities = data.get('identities', set())
            self.add_node(jid, node)
            self.get_node(jid, node)['info']['identities'] = identities

    def del_identity(self, jid, node, ifrom, data):
        """
        Remove an identity from a JID/node combination.

        The data parameter may provide:
            category -- The general category to which the agent belonged.
            itype    -- A more specific designation with the category.
            name     -- Optional human readable name for this identity.
            lang     -- Optional, standard xml:lang value.
        """
        with self.lock:
            if self.node_exists(jid, node):
                self.get_node(jid, node)['info'].del_identity(
                        data.get('category', ''),
                        data.get('itype', ''),
                        data.get('name', None),
                        data.get('lang', None))

    def del_identities(self, jid, node, ifrom, data):
        """
        Remove all identities from a JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if self.node_exists(jid, node):
                del self.get_node(jid, node)['info']['identities']

    def add_feature(self, jid, node, ifrom, data):
        """
        Add a feature to a JID/node combination.

        The data parameter should include:
            feature -- The namespace of the supported feature.
        """
        with self.lock:
            self.add_node(jid, node)
            self.get_node(jid, node)['info'].add_feature(
                    data.get('feature', ''))

    def set_features(self, jid, node, ifrom, data):
        """
        Add or replace all features for a JID/node combination.

        The data parameter should include:
            features -- The new set of supported features.
        """
        with self.lock:
            features = data.get('features', set())
            self.add_node(jid, node)
            self.get_node(jid, node)['info']['features'] = features

    def del_feature(self, jid, node, ifrom, data):
        """
        Remove a feature from a JID/node combination.

        The data parameter should include:
            feature -- The namespace of the removed feature.
        """
        with self.lock:
            if self.node_exists(jid, node):
                self.get_node(jid, node)['info'].del_feature(
                        data.get('feature', ''))

    def del_features(self, jid, node, ifrom, data):
        """
        Remove all features from a JID/node combination.

        The data parameter is not used.
        """
        with self.lock:
            if not self.node_exists(jid, node):
                return
            del self.get_node(jid, node)['info']['features']

    def add_item(self, jid, node, ifrom, data):
        """
        Add an item to a JID/node combination.

        The data parameter may include:
            ijid  -- The JID for the item.
            inode -- Optional additional information to reference
                     non-addressable items.
            name  -- Optional human readable name for the item.
        """
        with self.lock:
            self.add_node(jid, node)
            self.get_node(jid, node)['items'].add_item(
                    data.get('ijid', ''),
                    node=data.get('inode', ''),
                    name=data.get('name', ''))

    def del_item(self, jid, node, ifrom, data):
        """
        Remove an item from a JID/node combination.

        The data parameter may include:
            ijid  -- JID of the item to remove.
            inode -- Optional extra identifying information.
        """
        with self.lock:
            if self.node_exists(jid, node):
                self.get_node(jid, node)['items'].del_item(
                        data.get('ijid', ''),
                        node=data.get('inode', None))

    def cache_info(self, jid, node, ifrom, data):
        """
        Cache disco information for an external JID.

        The data parameter is the Iq result stanza
        containing the disco info to cache, or
        the disco#info substanza itself.
        """
        with self.lock:
            if isinstance(data, Iq):
                data = data['disco_info']

            self.add_node(jid, node, ifrom)
            self.get_node(jid, node, ifrom)['info'] = data

    def get_cached_info(self, jid, node, ifrom, data):
        """
        Retrieve cached disco info data.

        The data parameter is not used.
        """
        with self.lock:
            if not self.node_exists(jid, node, ifrom):
                return None
            else:
                return self.get_node(jid, node, ifrom)['info']
