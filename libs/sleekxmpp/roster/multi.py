"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.stanza import Presence
from sleekxmpp.xmlstream import JID
from sleekxmpp.roster import RosterNode


class Roster(object):

    """
    SleekXMPP's roster manager.

    The roster is divided into "nodes", where each node is responsible
    for a single JID. While the distinction is not strictly necessary
    for client connections, it is a necessity for components that use
    multiple JIDs.

    Rosters may be stored and persisted in an external datastore. An
    interface object to the datastore that loads and saves roster items may
    be provided. See the documentation for the RosterItem class for the
    methods that the datastore interface object must provide.

    Attributes:
        xmpp           -- The main SleekXMPP instance.
        db             -- Optional interface object to an external datastore.
        auto_authorize -- Default auto_authorize value for new roster nodes.
                          Defaults to True.
        auto_subscribe -- Default auto_subscribe value for new roster nodes.
                          Defaults to True.

    Methods:
        add           -- Create a new roster node for a JID.
        send_presence -- Shortcut for sending a presence stanza.
    """

    def __init__(self, xmpp, db=None):
        """
        Create a new roster.

        Arguments:
            xmpp -- The main SleekXMPP instance.
            db   -- Optional interface object to a datastore.
        """
        self.xmpp = xmpp
        self.db = db
        self._auto_authorize = True
        self._auto_subscribe = True
        self._rosters = {}

        if self.db:
            for node in self.db.entries(None, {}):
                self.add(node)

        self.xmpp.add_filter('out', self._save_last_status)

    def _save_last_status(self, stanza):

        if isinstance(stanza, Presence):
            sfrom = stanza['from'].full
            sto = stanza['to'].full

            if not sfrom:
                sfrom = self.xmpp.boundjid

            if stanza['type'] in stanza.showtypes or \
               stanza['type'] in ('available', 'unavailable'):
                if sto:
                    self[sfrom][sto].last_status = stanza
                else:
                    self[sfrom].last_status = stanza
                    with self[sfrom]._last_status_lock:
                        for jid in self[sfrom]:
                            self[sfrom][jid].last_status = None

                if not self.xmpp.sentpresence:
                    self.xmpp.event('sent_presence')
                    self.xmpp.sentpresence = True

        return stanza

    def __getitem__(self, key):
        """
        Return the roster node for a JID.

        A new roster node will be created if one
        does not already exist.

        Arguments:
            key -- Return the roster for this JID.
        """
        if key is None:
            key = self.xmpp.boundjid
        if not isinstance(key, JID):
            key = JID(key)
        key = key.bare

        if key not in self._rosters:
            self.add(key)
            self._rosters[key].auto_authorize = self.auto_authorize
            self._rosters[key].auto_subscribe = self.auto_subscribe
        return self._rosters[key]

    def keys(self):
        """Return the JIDs managed by the roster."""
        return self._rosters.keys()

    def __iter__(self):
        """Iterate over the roster nodes."""
        return self._rosters.__iter__()

    def add(self, node):
        """
        Add a new roster node for the given JID.

        Arguments:
            node -- The JID for the new roster node.
        """
        if not isinstance(node, JID):
            node = JID(node)

        node = node.bare
        if node not in self._rosters:
            self._rosters[node] = RosterNode(self.xmpp, node, self.db)

    def set_backend(self, db=None, save=True):
        """
        Set the datastore interface object for the roster.

        Arguments:
            db -- The new datastore interface.
            save -- If True, save the existing state to the new
                    backend datastore. Defaults to True.
        """
        self.db = db
        existing_entries = set(self._rosters)
        new_entries = set(self.db.entries(None, {}))

        for node in existing_entries:
            self._rosters[node].set_backend(db, save)
        for node in new_entries - existing_entries:
            self.add(node)

    def reset(self):
        """
        Reset the state of the roster to forget any current
        presence information. Useful after a disconnection occurs.
        """
        for node in self:
            self[node].reset()

    def send_presence(self, **kwargs):
        """
        Create, initialize, and send a Presence stanza.

        If no recipient is specified, send the presence immediately.
        Otherwise, forward the send request to the recipient's roster
        entry for processing.

        Arguments:
            pshow     -- The presence's show value.
            pstatus   -- The presence's status message.
            ppriority -- This connections' priority.
            pto       -- The recipient of a directed presence.
            pfrom     -- The sender of a directed presence, which should
                         be the owner JID plus resource.
            ptype     -- The type of presence, such as 'subscribe'.
            pnick     -- Optional nickname of the presence's sender.
        """
        if self.xmpp.is_component and not kwargs.get('pfrom', ''):
            kwargs['pfrom'] = self.jid
        self.xmpp.send_presence(**kwargs)

    @property
    def auto_authorize(self):
        """
        Auto accept or deny subscription requests.

        If True, auto accept subscription requests.
        If False, auto deny subscription requests.
        If None, don't automatically respond.
        """
        return self._auto_authorize

    @auto_authorize.setter
    def auto_authorize(self, value):
        """
        Auto accept or deny subscription requests.

        If True, auto accept subscription requests.
        If False, auto deny subscription requests.
        If None, don't automatically respond.
        """
        self._auto_authorize = value
        for node in self._rosters:
            self._rosters[node].auto_authorize = value

    @property
    def auto_subscribe(self):
        """
        Auto send requests for mutual subscriptions.

        If True, auto send mutual subscription requests.
        """
        return self._auto_subscribe

    @auto_subscribe.setter
    def auto_subscribe(self, value):
        """
        Auto send requests for mutual subscriptions.

        If True, auto send mutual subscription requests.
        """
        self._auto_subscribe = value
        for node in self._rosters:
            self._rosters[node].auto_subscribe = value

    def __repr__(self):
        return repr(self._rosters)
