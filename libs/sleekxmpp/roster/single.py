"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import threading

from sleekxmpp.xmlstream import JID
from sleekxmpp.roster import RosterItem


class RosterNode(object):

    """
    A roster node is a roster for a single JID.

    Attributes:
        xmpp           -- The main SleekXMPP instance.
        jid            -- The JID that owns the roster node.
        db             -- Optional interface to an external datastore.
        auto_authorize -- Determines how authorizations are handled:
                            True  -- Accept all subscriptions.
                            False -- Reject all subscriptions.
                            None  -- Subscriptions must be
                                     manually authorized.
                          Defaults to True.
        auto_subscribe -- Determines if bi-directional subscriptions
                          are created after automatically authrorizing
                          a subscription request.
                          Defaults to True
        last_status    -- The last sent presence status that was broadcast
                          to all contact JIDs.

    Methods:
        add           -- Add a JID to the roster.
        update        -- Update a JID's subscription information.
        subscribe     -- Subscribe to a JID.
        unsubscribe   -- Unsubscribe from a JID.
        remove        -- Remove a JID from the roster.
        presence      -- Return presence information for a JID's resources.
        send_presence -- Shortcut for sending a presence stanza.
    """

    def __init__(self, xmpp, jid, db=None):
        """
        Create a roster node for a JID.

        Arguments:
            xmpp -- The main SleekXMPP instance.
            jid  -- The JID that owns the roster.
            db   -- Optional interface to an external datastore.
        """
        self.xmpp = xmpp
        self.jid = jid
        self.db = db
        self.auto_authorize = True
        self.auto_subscribe = True
        self.last_status = None
        self._version = ''
        self._jids = {}
        self._last_status_lock = threading.Lock()

        if self.db:
            if hasattr(self.db, 'version'):
                self._version = self.db.version(self.jid)
            for jid in self.db.entries(self.jid):
                self.add(jid)

    @property
    def version(self):
        """Retrieve the roster's version ID."""
        if self.db and hasattr(self.db, 'version'):
            self._version = self.db.version(self.jid)
        return self._version

    @version.setter
    def version(self, version):
        """Set the roster's version ID."""
        self._version = version
        if self.db and hasattr(self.db, 'set_version'):
            self.db.set_version(self.jid, version)

    def __getitem__(self, key):
        """
        Return the roster item for a subscribed JID.

        A new item entry will be created if one does not already exist.
        """
        if key is None:
            key = JID('')
        if not isinstance(key, JID):
            key = JID(key)
        key = key.bare
        if key not in self._jids:
            self.add(key, save=True)
        return self._jids[key]

    def __delitem__(self, key):
        """
        Remove a roster item from the local storage.

        To remove an item from the server, use the remove() method.
        """
        if key is None:
            key = JID('')
        if not isinstance(key, JID):
            key = JID(key)
        key = key.bare
        if key in self._jids:
            del self._jids[key]

    def __len__(self):
        """Return the number of JIDs referenced by the roster."""
        return len(self._jids)

    def keys(self):
        """Return a list of all subscribed JIDs."""
        return self._jids.keys()

    def has_jid(self, jid):
        """Returns whether the roster has a JID."""
        return jid in self._jids

    def groups(self):
        """Return a dictionary mapping group names to JIDs."""
        result = {}
        for jid in self._jids:
            groups = self._jids[jid]['groups']
            if not groups:
                if '' not in result:
                    result[''] = []
                result[''].append(jid)
            for group in groups:
                if group not in result:
                    result[group] = []
                result[group].append(jid)
        return result

    def __iter__(self):
        """Iterate over the roster items."""
        return self._jids.__iter__()

    def set_backend(self, db=None, save=True):
        """
        Set the datastore interface object for the roster node.

        Arguments:
            db -- The new datastore interface.
            save -- If True, save the existing state to the new
                    backend datastore. Defaults to True.
        """
        self.db = db
        existing_entries = set(self._jids)
        new_entries = set(self.db.entries(self.jid, {}))

        for jid in existing_entries:
            self._jids[jid].set_backend(db, save)
        for jid in new_entries - existing_entries:
            self.add(jid)

    def add(self, jid, name='', groups=None, afrom=False, ato=False,
            pending_in=False, pending_out=False, whitelisted=False,
            save=False):
        """
        Add a new roster item entry.

        Arguments:
            jid         -- The JID for the roster item.
            name        -- An alias for the JID.
            groups      -- A list of group names.
            afrom       -- Indicates if the JID has a subscription state
                           of 'from'. Defaults to False.
            ato         -- Indicates if the JID has a subscription state
                           of 'to'. Defaults to False.
            pending_in  -- Indicates if the JID has sent a subscription
                           request to this connection's JID.
                           Defaults to False.
            pending_out -- Indicates if a subscription request has been sent
                           to this JID.
                           Defaults to False.
            whitelisted -- Indicates if a subscription request from this JID
                           should be automatically authorized.
                           Defaults to False.
            save        -- Indicates if the item should be persisted
                           immediately to an external datastore,
                           if one is used.
                           Defaults to False.
        """
        if isinstance(jid, JID):
            key = jid.bare
        else:
            key = jid

        state = {'name': name,
                 'groups': groups or [],
                 'from': afrom,
                 'to': ato,
                 'pending_in': pending_in,
                 'pending_out': pending_out,
                 'whitelisted': whitelisted,
                 'subscription': 'none'}
        self._jids[key] = RosterItem(self.xmpp, jid, self.jid,
                                     state=state, db=self.db,
                                     roster=self)
        if save:
            self._jids[key].save()

    def subscribe(self, jid):
        """
        Subscribe to the given JID.

        Arguments:
            jid -- The JID to subscribe to.
        """
        self[jid].subscribe()

    def unsubscribe(self, jid):
        """
        Unsubscribe from the given JID.

        Arguments:
            jid -- The JID to unsubscribe from.
        """
        self[jid].unsubscribe()

    def remove(self, jid):
        """
        Remove a JID from the roster.

        Arguments:
            jid -- The JID to remove.
        """
        self[jid].remove()
        if not self.xmpp.is_component:
            return self.update(jid, subscription='remove')

    def update(self, jid, name=None, subscription=None, groups=[],
                     block=True, timeout=None, callback=None):
        """
        Update a JID's subscription information.

        Arguments:
            jid          -- The JID to update.
            name         -- Optional alias for the JID.
            subscription -- The subscription state. May be one of: 'to',
                            'from', 'both', 'none', or 'remove'.
            groups       -- A list of group names.
            block        -- Specify if the roster request will block
                            until a response is received, or a timeout
                            occurs. Defaults to True.
            timeout      -- The length of time (in seconds) to wait
                            for a response before continuing if blocking
                            is used. Defaults to self.response_timeout.
            callback     -- Optional reference to a stream handler function.
                            Will be executed when the roster is received.
                            Implies block=False.
        """
        self[jid]['name'] = name
        self[jid]['groups'] = groups
        self[jid].save()

        if not self.xmpp.is_component:
            iq = self.xmpp.Iq()
            iq['type'] = 'set'
            iq['roster']['items'] = {jid: {'name': name,
                                           'subscription': subscription,
                                           'groups': groups}}

            return iq.send(block, timeout, callback)

    def presence(self, jid, resource=None):
        """
        Retrieve the presence information of a JID.

        May return either all online resources' status, or
        a single resource's status.

        Arguments:
            jid      -- The JID to lookup.
            resource -- Optional resource for returning
                        only the status of a single connection.
        """
        if resource is None:
            return self[jid].resources

        default_presence = {'status': '',
                            'priority': 0,
                            'show': ''}
        return self[jid].resources.get(resource,
                                       default_presence)

    def reset(self):
        """
        Reset the state of the roster to forget any current
        presence information. Useful after a disconnection occurs.
        """
        for jid in self:
            self[jid].reset()

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

    def send_last_presence(self):
        if self.last_status is None:
            self.send_presence()
        else:
            pres = self.last_status
            if self.xmpp.is_component:
                pres['from'] = self.jid
            else:
                del pres['from']
            pres.send()

    def __repr__(self):
        return repr(self._jids)
