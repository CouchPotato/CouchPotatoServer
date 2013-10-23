"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""


class RosterItem(object):

    """
    A RosterItem is a single entry in a roster node, and tracks
    the subscription state and user annotations of a single JID.

    Roster items may use an external datastore to persist roster data
    across sessions. Client applications will not need to use this
    functionality, but is intended for components that do not have their
    roster persisted automatically by the XMPP server.

    Roster items provide many methods for handling incoming presence
    stanzas that ensure that response stanzas are sent according to
    RFC 3921.

    The external datastore is accessed through a provided interface
    object which is stored in self.db. The interface object MUST
    provide two methods: load and save, both of which are responsible
    for working with a single roster item. A private dictionary,
    self._db_state, is used to store any metadata needed by the
    interface, such as the row ID of a roster item, etc.

    Interface for self.db.load:
        load(owner_jid, jid, db_state):
          owner_jid  -- The JID that owns the roster.
          jid        -- The JID of the roster item.
          db_state   -- A dictionary containing any data saved
                        by the interface object after a save()
                        call. Will typically have the equivalent
                        of a 'row_id' value.

    Interface for self.db.save:
        save(owner_jid, jid, item_state, db_state):
          owner_jid  -- The JID that owns the roster.
          jid        -- The JID of the roster item.
          item_state -- A dictionary containing the fields:
                        'from', 'to', 'pending_in', 'pending_out',
                        'whitelisted', 'subscription', 'name',
                        and 'groups'.
          db_state   -- A dictionary provided for persisting
                        datastore specific information. Typically,
                        a value equivalent to 'row_id' will be
                        stored here.

    State Fields:
        from         -- Indicates if a subscription of type 'from'
                        has been authorized.
        to           -- Indicates if a subscription of type 'to' has
                        been authorized.
        pending_in   -- Indicates if a subscription request has been
                        received from this JID and it has not been
                        authorized yet.
        pending_out  -- Indicates if a subscription request has been sent
                        to this JID and it has not been accepted yet.
        subscription -- Returns one of: 'to', 'from', 'both', or 'none'
                        based on the states of from, to, pending_in,
                        and pending_out. Assignment to this value does
                        not affect the states of the other values.
        whitelisted  -- Indicates if a subscription request from this
                        JID should be automatically accepted.
        name         -- A user supplied alias for the JID.
        groups       -- A list of group names for the JID.

    Attributes:
        xmpp        -- The main SleekXMPP instance.
        owner       -- The JID that owns the roster.
        jid         -- The JID for the roster item.
        db          -- Optional datastore interface object.
        last_status -- The last presence sent to this JID.
        resources   -- A dictionary of online resources for this JID.
                       Will contain the fields 'show', 'status',
                       and 'priority'.

    Methods:
        load                -- Retrieve the roster item from an
                               external datastore, if one was provided.
        save                -- Save the roster item to an external
                               datastore, if one was provided.
        remove              -- Remove a subscription to the JID and revoke
                               its whitelisted status.
        subscribe           -- Subscribe to the JID.
        authorize           -- Accept a subscription from the JID.
        unauthorize         -- Deny a subscription from the JID.
        unsubscribe         -- Unsubscribe from the JID.
        send_presence       -- Send a directed presence to the JID.
        send_last_presence  -- Resend the last sent presence.
        handle_available    -- Update the JID's resource information.
        handle_unavailable  -- Update the JID's resource information.
        handle_subscribe    -- Handle a subscription request.
        handle_subscribed   -- Handle a notice that a subscription request
                               was authorized by the JID.
        handle_unsubscribe  -- Handle an unsubscribe request.
        handle_unsubscribed -- Handle a notice that a subscription was
                               removed by the JID.
        handle_probe        -- Handle a presence probe query.
    """

    def __init__(self, xmpp, jid, owner=None,
                 state=None, db=None, roster=None):
        """
        Create a new roster item.

        Arguments:
            xmpp   -- The main SleekXMPP instance.
            jid    -- The item's JID.
            owner  -- The roster owner's JID. Defaults
                      so self.xmpp.boundjid.bare.
            state  -- A dictionary of initial state values.
            db     -- An optional interface to an external datastore.
            roster -- The roster object containing this entry.
        """
        self.xmpp = xmpp
        self.jid = jid
        self.owner = owner or self.xmpp.boundjid.bare
        self.last_status = None
        self.resources = {}
        self.roster = roster
        self.db = db
        self._state = state or {
                'from': False,
                'to': False,
                'pending_in': False,
                'pending_out': False,
                'whitelisted': False,
                'subscription': 'none',
                'name': '',
                'groups': []}

        self._db_state = {}
        self.load()

    def set_backend(self, db=None, save=True):
        """
        Set the datastore interface object for the roster item.

        Arguments:
            db   -- The new datastore interface.
            save -- If True, save the existing state to the new
                    backend datastore. Defaults to True.
        """
        self.db = db
        if save:
            self.save()
        self.load()

    def load(self):
        """
        Load the item's state information from an external datastore,
        if one has been provided.
        """
        if self.db:
            item = self.db.load(self.owner, self.jid,
                                       self._db_state)
            if item:
                self['name'] = item['name']
                self['groups'] = item['groups']
                self['from'] = item['from']
                self['to'] = item['to']
                self['whitelisted'] = item['whitelisted']
                self['pending_out'] = item['pending_out']
                self['pending_in'] = item['pending_in']
                self['subscription'] = self._subscription()
            return self._state
        return None

    def save(self, remove=False):
        """
        Save the item's state information to an external datastore,
        if one has been provided.

        Arguments:
            remove -- If True, expunge the item from the datastore.
        """
        self['subscription'] = self._subscription()
        if remove:
            self._state['removed'] = True
        if self.db:
            self.db.save(self.owner, self.jid,
                         self._state, self._db_state)

        # Finally, remove the in-memory copy if needed.
        if remove:
            del self.xmpp.roster[self.owner][self.jid]

    def __getitem__(self, key):
        """Return a state field's value."""
        if key in self._state:
            if key == 'subscription':
                return self._subscription()
            return self._state[key]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        """
        Set the value of a state field.

        For boolean states, the values True, 'true', '1', 'on',
        and 'yes' are accepted as True; all others are False.

        Arguments:
            key   -- The state field to modify.
            value -- The new value of the state field.
        """
        if key in self._state:
            if key in ['name', 'subscription', 'groups']:
                self._state[key] = value
            else:
                value = str(value).lower()
                self._state[key] = value in ('true', '1', 'on', 'yes')
        else:
            raise KeyError

    def _subscription(self):
        """Return the proper subscription type based on current state."""
        if self['to'] and self['from']:
            return 'both'
        elif self['from']:
            return 'from'
        elif self['to']:
            return 'to'
        else:
            return 'none'

    def remove(self):
        """
        Remove a JID's whitelisted status and unsubscribe if a
        subscription exists.
        """
        if self['to']:
            p = self.xmpp.Presence()
            p['to'] = self.jid
            p['type'] = 'unsubscribe'
            if self.xmpp.is_component:
                p['from'] = self.owner
            p.send()
            self['to'] = False
        self['whitelisted'] = False
        self.save()

    def subscribe(self):
        """Send a subscription request to the JID."""
        p = self.xmpp.Presence()
        p['to'] = self.jid
        p['type'] = 'subscribe'
        if self.xmpp.is_component:
            p['from'] = self.owner
        self['pending_out'] = True
        self.save()
        p.send()

    def authorize(self):
        """Authorize a received subscription request from the JID."""
        self['from'] = True
        self['pending_in'] = False
        self.save()
        self._subscribed()
        self.send_last_presence()

    def unauthorize(self):
        """Deny a received subscription request from the JID."""
        self['from'] = False
        self['pending_in'] = False
        self.save()
        self._unsubscribed()
        p = self.xmpp.Presence()
        p['to'] = self.jid
        p['type'] = 'unavailable'
        if self.xmpp.is_component:
            p['from'] = self.owner
        p.send()

    def _subscribed(self):
        """Handle acknowledging a subscription."""
        p = self.xmpp.Presence()
        p['to'] = self.jid
        p['type'] = 'subscribed'
        if self.xmpp.is_component:
            p['from'] = self.owner
        p.send()

    def unsubscribe(self):
        """Unsubscribe from the JID."""
        p = self.xmpp.Presence()
        p['to'] = self.jid
        p['type'] = 'unsubscribe'
        if self.xmpp.is_component:
            p['from'] = self.owner
        self.save()
        p.send()

    def _unsubscribed(self):
        """Handle acknowledging an unsubscribe request."""
        p = self.xmpp.Presence()
        p['to'] = self.jid
        p['type'] = 'unsubscribed'
        if self.xmpp.is_component:
            p['from'] = self.owner
        p.send()

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
            kwargs['pfrom'] = self.owner
        if not kwargs.get('pto', ''):
            kwargs['pto'] = self.jid
        self.xmpp.send_presence(**kwargs)

    def send_last_presence(self):
        if self.last_status is None:
            pres = self.roster.last_status
            if pres is None:
                self.send_presence()
            else:
                pres['to'] = self.jid
                if self.xmpp.is_component:
                    pres['from'] = self.owner
                else:
                    del pres['from']
                pres.send()
        else:
            self.last_status.send()

    def handle_available(self, presence):
        resource = presence['from'].resource
        data = {'status': presence['status'],
                'show': presence['show'],
                'priority': presence['priority']}
        got_online = not self.resources
        if resource not in self.resources:
            self.resources[resource] = {}
        old_status = self.resources[resource].get('status', '')
        old_show = self.resources[resource].get('show', None)
        self.resources[resource].update(data)
        if got_online:
            self.xmpp.event('got_online', presence)
        if old_show != presence['show'] or old_status != presence['status']:
            self.xmpp.event('changed_status', presence)

    def handle_unavailable(self, presence):
        resource = presence['from'].resource
        if not self.resources:
            return
        if resource in self.resources:
            del self.resources[resource]
        self.xmpp.event('changed_status', presence)
        if not self.resources:
            self.xmpp.event('got_offline', presence)

    def handle_subscribe(self, presence):
        """
        +------------------------------------------------------------------+
        |  EXISTING STATE          |  DELIVER?  |  NEW STATE               |
        +------------------------------------------------------------------+
        |  "None"                  |  yes       |  "None + Pending In"     |
        |  "None + Pending Out"    |  yes       |  "None + Pending Out/In" |
        |  "None + Pending In"     |  no        |  no state change         |
        |  "None + Pending Out/In" |  no        |  no state change         |
        |  "To"                    |  yes       |  "To + Pending In"       |
        |  "To + Pending In"       |  no        |  no state change         |
        |  "From"                  |  no *      |  no state change         |
        |  "From + Pending Out"    |  no *      |  no state change         |
        |  "Both"                  |  no *      |  no state change         |
        +------------------------------------------------------------------+
        """
        if self.xmpp.is_component:
            if not self['from'] and not self['pending_in']:
                self['pending_in'] = True
                self.xmpp.event('roster_subscription_request', presence)
            elif self['from']:
                self._subscribed()
            self.save()
        else:
            #server shouldn't send an invalid subscription request
            self.xmpp.event('roster_subscription_request', presence)

    def handle_subscribed(self, presence):
        """
        +------------------------------------------------------------------+
        |  EXISTING STATE          |  DELIVER?  |  NEW STATE               |
        +------------------------------------------------------------------+
        |  "None"                  |  no        |  no state change         |
        |  "None + Pending Out"    |  yes       |  "To"                    |
        |  "None + Pending In"     |  no        |  no state change         |
        |  "None + Pending Out/In" |  yes       |  "To + Pending In"       |
        |  "To"                    |  no        |  no state change         |
        |  "To + Pending In"       |  no        |  no state change         |
        |  "From"                  |  no        |  no state change         |
        |  "From + Pending Out"    |  yes       |  "Both"                  |
        |  "Both"                  |  no        |  no state change         |
        +------------------------------------------------------------------+
        """
        if self.xmpp.is_component:
            if not self['to'] and self['pending_out']:
                self['pending_out'] = False
                self['to'] = True
                self.xmpp.event('roster_subscription_authorized', presence)
            self.save()
        else:
            self.xmpp.event('roster_subscription_authorized', presence)

    def handle_unsubscribe(self, presence):
        """
        +------------------------------------------------------------------+
        |  EXISTING STATE          |  DELIVER?  |  NEW STATE               |
        +------------------------------------------------------------------+
        |  "None"                  |  no        |  no state change         |
        |  "None + Pending Out"    |  no        |  no state change         |
        |  "None + Pending In"     |  yes *     |  "None"                  |
        |  "None + Pending Out/In" |  yes *     |  "None + Pending Out"    |
        |  "To"                    |  no        |  no state change         |
        |  "To + Pending In"       |  yes *     |  "To"                    |
        |  "From"                  |  yes *     |  "None"                  |
        |  "From + Pending Out"    |  yes *     |  "None + Pending Out     |
        |  "Both"                  |  yes *     |  "To"                    |
        +------------------------------------------------------------------+
        """
        if self.xmpp.is_component:
            if not self['from']  and self['pending_in']:
                self['pending_in'] = False
                self._unsubscribed()
            elif self['from']:
                self['from'] = False
                self._unsubscribed()
                self.xmpp.event('roster_subscription_remove', presence)
            self.save()
        else:
            self.xmpp.event('roster_subscription_remove', presence)

    def handle_unsubscribed(self, presence):
        """
        +------------------------------------------------------------------+
        |  EXISTING STATE          |  DELIVER?  |  NEW STATE               |
        +------------------------------------------------------------------+
        |  "None"                  |  no        |  no state change         |
        |  "None + Pending Out"    |  yes       |  "None"                  |
        |  "None + Pending In"     |  no        |  no state change         |
        |  "None + Pending Out/In" |  yes       |  "None + Pending In"     |
        |  "To"                    |  yes       |  "None"                  |
        |  "To + Pending In"       |  yes       |  "None + Pending In"     |
        |  "From"                  |  no        |  no state change         |
        |  "From + Pending Out"    |  yes       |  "From"                  |
        |  "Both"                  |  yes       |  "From"                  |
        +------------------------------------------------------------------
        """
        if self.xmpp.is_component:
            if not self['to'] and self['pending_out']:
                self['pending_out'] = False
            elif self['to'] and not self['pending_out']:
                self['to'] = False
                self.xmpp.event('roster_subscription_removed', presence)
            self.save()
        else:
            self.xmpp.event('roster_subscription_removed', presence)

    def handle_probe(self, presence):
        if self['from']:
            self.send_last_presence()
        if self['pending_out']:
            self.subscribe()
        if not self['from']:
            self._unsubscribed()

    def reset(self):
        """
        Forgot current resource presence information as part of
        a roster reset request.
        """
        self.resources = {}

    def __repr__(self):
        return repr(self._state)
