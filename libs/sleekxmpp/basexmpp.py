# -*- coding: utf-8 -*-
"""
    sleekxmpp.basexmpp
    ~~~~~~~~~~~~~~~~~~

    This module provides the common XMPP functionality
    for both clients and components.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from __future__ import with_statement, unicode_literals

import sys
import logging
import threading

import sleekxmpp
from sleekxmpp import plugins, features, roster
from sleekxmpp.api import APIRegistry
from sleekxmpp.exceptions import IqError, IqTimeout

from sleekxmpp.stanza import Message, Presence, Iq, StreamError
from sleekxmpp.stanza.roster import Roster
from sleekxmpp.stanza.nick import Nick
from sleekxmpp.stanza.htmlim import HTMLIM

from sleekxmpp.xmlstream import XMLStream, JID
from sleekxmpp.xmlstream import ET, register_stanza_plugin
from sleekxmpp.xmlstream.matcher import MatchXPath
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.stanzabase import XML_NS

from sleekxmpp.features import *
from sleekxmpp.plugins import PluginManager, register_plugin, load_plugin


log = logging.getLogger(__name__)

# In order to make sure that Unicode is handled properly
# in Python 2.x, reset the default encoding.
if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')


class BaseXMPP(XMLStream):

    """
    The BaseXMPP class adapts the generic XMLStream class for use
    with XMPP. It also provides a plugin mechanism to easily extend
    and add support for new XMPP features.

    :param default_ns: Ensure that the correct default XML namespace
                       is used during initialization.
    """

    def __init__(self, jid='', default_ns='jabber:client'):
        XMLStream.__init__(self)

        self.default_ns = default_ns
        self.stream_ns = 'http://etherx.jabber.org/streams'
        self.namespace_map[self.stream_ns] = 'stream'

        #: An identifier for the stream as given by the server.
        self.stream_id = None

        #: The JabberID (JID) requested for this connection.
        self.requested_jid = JID(jid, cache_lock=True)

        #: The JabberID (JID) used by this connection,
        #: as set after session binding. This may even be a
        #: different bare JID than what was requested.
        self.boundjid = JID(jid, cache_lock=True)

        self._expected_server_name = self.boundjid.host
        self._redirect_attempts = 0

        #: The maximum number of consecutive see-other-host
        #: redirections that will be followed before quitting.
        self.max_redirects = 5

        self.session_bind_event = threading.Event()

        #: A dictionary mapping plugin names to plugins.
        self.plugin = PluginManager(self)

        #: Configuration options for whitelisted plugins.
        #: If a plugin is registered without any configuration,
        #: and there is an entry here, it will be used.
        self.plugin_config = {}

        #: A list of plugins that will be loaded if
        #: :meth:`register_plugins` is called.
        self.plugin_whitelist = []

        #: The main roster object. This roster supports multiple
        #: owner JIDs, as in the case for components. For clients
        #: which only have a single JID, see :attr:`client_roster`.
        self.roster = roster.Roster(self)
        self.roster.add(self.boundjid)

        #: The single roster for the bound JID. This is the
        #: equivalent of::
        #:
        #:     self.roster[self.boundjid.bare]
        self.client_roster = self.roster[self.boundjid]

        #: The distinction between clients and components can be
        #: important, primarily for choosing how to handle the
        #: ``'to'`` and ``'from'`` JIDs of stanzas.
        self.is_component = False

        #: Messages may optionally be tagged with ID values. Setting
        #: :attr:`use_message_ids` to `True` will assign all outgoing
        #: messages an ID. Some plugin features require enabling
        #: this option.
        self.use_message_ids = False

        #: Presence updates may optionally be tagged with ID values.
        #: Setting :attr:`use_message_ids` to `True` will assign all
        #: outgoing messages an ID.
        self.use_presence_ids = False

        #: The API registry is a way to process callbacks based on
        #: JID+node combinations. Each callback in the registry is
        #: marked with:
        #:
        #:   - An API name, e.g. xep_0030
        #:   - The name of an action, e.g. get_info
        #:   - The JID that will be affected
        #:   - The node that will be affected
        #:
        #: API handlers with no JID or node will act as global handlers,
        #: while those with a JID and no node will service all nodes
        #: for a JID, and handlers with both a JID and node will be
        #: used only for that specific combination. The handler that
        #: provides the most specificity will be used.
        self.api = APIRegistry(self)

        #: Flag indicating that the initial presence broadcast has
        #: been sent. Until this happens, some servers may not
        #: behave as expected when sending stanzas.
        self.sentpresence = False

        #: A reference to :mod:`sleekxmpp.stanza` to make accessing
        #: stanza classes easier.
        self.stanza = sleekxmpp.stanza

        self.register_handler(
            Callback('IM',
                     MatchXPath('{%s}message/{%s}body' % (self.default_ns,
                                                          self.default_ns)),
                     self._handle_message))
        self.register_handler(
            Callback('Presence',
                     MatchXPath("{%s}presence" % self.default_ns),
                     self._handle_presence))

        self.register_handler(
            Callback('Stream Error',
                     MatchXPath("{%s}error" % self.stream_ns),
                     self._handle_stream_error))

        self.add_event_handler('session_start',
                               self._handle_session_start)
        self.add_event_handler('disconnected',
                               self._handle_disconnected)
        self.add_event_handler('presence_available',
                               self._handle_available)
        self.add_event_handler('presence_dnd',
                               self._handle_available)
        self.add_event_handler('presence_xa',
                               self._handle_available)
        self.add_event_handler('presence_chat',
                               self._handle_available)
        self.add_event_handler('presence_away',
                               self._handle_available)
        self.add_event_handler('presence_unavailable',
                               self._handle_unavailable)
        self.add_event_handler('presence_subscribe',
                               self._handle_subscribe)
        self.add_event_handler('presence_subscribed',
                               self._handle_subscribed)
        self.add_event_handler('presence_unsubscribe',
                               self._handle_unsubscribe)
        self.add_event_handler('presence_unsubscribed',
                               self._handle_unsubscribed)
        self.add_event_handler('roster_subscription_request',
                               self._handle_new_subscription)

        # Set up the XML stream with XMPP's root stanzas.
        self.register_stanza(Message)
        self.register_stanza(Iq)
        self.register_stanza(Presence)
        self.register_stanza(StreamError)

        # Initialize a few default stanza plugins.
        register_stanza_plugin(Iq, Roster)
        register_stanza_plugin(Message, Nick)
        register_stanza_plugin(Message, HTMLIM)

    def start_stream_handler(self, xml):
        """Save the stream ID once the streams have been established.

        :param xml: The incoming stream's root element.
        """
        self.stream_id = xml.get('id', '')
        self.stream_version = xml.get('version', '')
        self.peer_default_lang = xml.get('{%s}lang' % XML_NS, None)

        if not self.is_component and not self.stream_version:
            log.warning('Legacy XMPP 0.9 protocol detected.')
            self.event('legacy_protocol')

    def process(self, *args, **kwargs):
        """Initialize plugins and begin processing the XML stream.

        The number of threads used for processing stream events is determined
        by :data:`HANDLER_THREADS`.

        :param bool block: If ``False``, then event dispatcher will run
                    in a separate thread, allowing for the stream to be
                    used in the background for another application.
                    Otherwise, ``process(block=True)`` blocks the current
                    thread. Defaults to ``False``.
        :param bool threaded: **DEPRECATED**
                    If ``True``, then event dispatcher will run
                    in a separate thread, allowing for the stream to be
                    used in the background for another application.
                    Defaults to ``True``. This does **not** mean that no
                    threads are used at all if ``threaded=False``.

        Regardless of these threading options, these threads will
        always exist:

        - The event queue processor
        - The send queue processor
        - The scheduler
        """
        for name in self.plugin:
            if not hasattr(self.plugin[name], 'post_inited'):
                if hasattr(self.plugin[name], 'post_init'):
                    self.plugin[name].post_init()
                self.plugin[name].post_inited = True
        return XMLStream.process(self, *args, **kwargs)

    def register_plugin(self, plugin, pconfig={}, module=None):
        """Register and configure  a plugin for use in this stream.

        :param plugin: The name of the plugin class. Plugin names must
                       be unique.
        :param pconfig: A dictionary of configuration data for the plugin.
                        Defaults to an empty dictionary.
        :param module: Optional refence to the module containing the plugin
                       class if using custom plugins.
        """

        # Use the global plugin config cache, if applicable
        if not pconfig:
            pconfig = self.plugin_config.get(plugin, {})

        if not self.plugin.registered(plugin):
            load_plugin(plugin, module)
        self.plugin.enable(plugin, pconfig)

    def register_plugins(self):
        """Register and initialize all built-in plugins.

        Optionally, the list of plugins loaded may be limited to those
        contained in :attr:`plugin_whitelist`.

        Plugin configurations stored in :attr:`plugin_config` will be used.
        """
        if self.plugin_whitelist:
            plugin_list = self.plugin_whitelist
        else:
            plugin_list = plugins.__all__

        for plugin in plugin_list:
            if plugin in plugins.__all__:
                self.register_plugin(plugin)
            else:
                raise NameError("Plugin %s not in plugins.__all__." % plugin)

    def __getitem__(self, key):
        """Return a plugin given its name, if it has been registered."""
        if key in self.plugin:
            return self.plugin[key]
        else:
            log.warning("Plugin '%s' is not loaded.", key)
            return False

    def get(self, key, default):
        """Return a plugin given its name, if it has been registered."""
        return self.plugin.get(key, default)

    def Message(self, *args, **kwargs):
        """Create a Message stanza associated with this stream."""
        msg = Message(self, *args, **kwargs)
        msg['lang'] = self.default_lang
        return msg

    def Iq(self, *args, **kwargs):
        """Create an Iq stanza associated with this stream."""
        return Iq(self, *args, **kwargs)

    def Presence(self, *args, **kwargs):
        """Create a Presence stanza associated with this stream."""
        pres = Presence(self, *args, **kwargs)
        pres['lang'] = self.default_lang
        return pres

    def make_iq(self, id=0, ifrom=None, ito=None, itype=None, iquery=None):
        """Create a new Iq stanza with a given Id and from JID.

        :param id: An ideally unique ID value for this stanza thread.
                   Defaults to 0.
        :param ifrom: The from :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param itype: The :class:`~sleekxmpp.stanza.iq.Iq`'s type,
                      one of: ``'get'``, ``'set'``, ``'result'``,
                      or ``'error'``.
        :param iquery: Optional namespace for adding a query element.
        """
        iq = self.Iq()
        iq['id'] = str(id)
        iq['to'] = ito
        iq['from'] = ifrom
        iq['type'] = itype
        iq['query'] = iquery
        return iq

    def make_iq_get(self, queryxmlns=None, ito=None, ifrom=None, iq=None):
        """Create an :class:`~sleekxmpp.stanza.iq.Iq` stanza of type ``'get'``.

        Optionally, a query element may be added.

        :param queryxmlns: The namespace of the query to use.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param ifrom: The ``'from'`` :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        """
        if not iq:
            iq = self.Iq()
        iq['type'] = 'get'
        iq['query'] = queryxmlns
        if ito:
            iq['to'] = ito
        if ifrom:
            iq['from'] = ifrom
        return iq

    def make_iq_result(self, id=None, ito=None, ifrom=None, iq=None):
        """
        Create an :class:`~sleekxmpp.stanza.iq.Iq` stanza of type
        ``'result'`` with the given ID value.

        :param id: An ideally unique ID value. May use :meth:`new_id()`.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param ifrom: The ``'from'`` :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        """
        if not iq:
            iq = self.Iq()
            if id is None:
                id = self.new_id()
            iq['id'] = id
        iq['type'] = 'result'
        if ito:
            iq['to'] = ito
        if ifrom:
            iq['from'] = ifrom
        return iq

    def make_iq_set(self, sub=None, ito=None, ifrom=None, iq=None):
        """
        Create an :class:`~sleekxmpp.stanza.iq.Iq` stanza of type ``'set'``.

        Optionally, a substanza may be given to use as the
        stanza's payload.

        :param sub: Either an
                    :class:`~sleekxmpp.xmlstream.stanzabase.ElementBase`
                    stanza object or an
                    :class:`~xml.etree.ElementTree.Element` XML object
                    to use as the :class:`~sleekxmpp.stanza.iq.Iq`'s payload.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param ifrom: The ``'from'`` :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        """
        if not iq:
            iq = self.Iq()
        iq['type'] = 'set'
        if sub != None:
            iq.append(sub)
        if ito:
            iq['to'] = ito
        if ifrom:
            iq['from'] = ifrom
        return iq

    def make_iq_error(self, id, type='cancel',
                      condition='feature-not-implemented',
                      text=None, ito=None, ifrom=None, iq=None):
        """
        Create an :class:`~sleekxmpp.stanza.iq.Iq` stanza of type ``'error'``.

        :param id: An ideally unique ID value. May use :meth:`new_id()`.
        :param type: The type of the error, such as ``'cancel'`` or
                     ``'modify'``. Defaults to ``'cancel'``.
        :param condition: The error condition. Defaults to
                          ``'feature-not-implemented'``.
        :param text: A message describing the cause of the error.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param ifrom: The ``'from'`` :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        """
        if not iq:
            iq = self.Iq()
        iq['id'] = id
        iq['error']['type'] = type
        iq['error']['condition'] = condition
        iq['error']['text'] = text
        if ito:
            iq['to'] = ito
        if ifrom:
            iq['from'] = ifrom
        return iq

    def make_iq_query(self, iq=None, xmlns='', ito=None, ifrom=None):
        """
        Create or modify an :class:`~sleekxmpp.stanza.iq.Iq` stanza
        to use the given query namespace.

        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        :param xmlns: The query's namespace.
        :param ito: The destination :class:`~sleekxmpp.xmlstream.jid.JID`
                    for this stanza.
        :param ifrom: The ``'from'`` :class:`~sleekxmpp.xmlstream.jid.JID`
                      to use for this stanza.
        """
        if not iq:
            iq = self.Iq()
        iq['query'] = xmlns
        if ito:
            iq['to'] = ito
        if ifrom:
            iq['from'] = ifrom
        return iq

    def make_query_roster(self, iq=None):
        """Create a roster query element.

        :param iq: Optionally use an existing stanza instead
                   of generating a new one.
        """
        if iq:
            iq['query'] = 'jabber:iq:roster'
        return ET.Element("{jabber:iq:roster}query")

    def make_message(self, mto, mbody=None, msubject=None, mtype=None,
                     mhtml=None, mfrom=None, mnick=None):
        """
        Create and initialize a new
        :class:`~sleekxmpp.stanza.message.Message` stanza.

        :param mto: The recipient of the message.
        :param mbody: The main contents of the message.
        :param msubject: Optional subject for the message.
        :param mtype: The message's type, such as ``'chat'`` or
                      ``'groupchat'``.
        :param mhtml: Optional HTML body content in the form of a string.
        :param mfrom: The sender of the message. if sending from a client,
                      be aware that some servers require that the full JID
                      of the sender be used.
        :param mnick: Optional nickname of the sender.
        """
        message = self.Message(sto=mto, stype=mtype, sfrom=mfrom)
        message['body'] = mbody
        message['subject'] = msubject
        if mnick is not None:
            message['nick'] = mnick
        if mhtml is not None:
            message['html']['body'] = mhtml
        return message

    def make_presence(self, pshow=None, pstatus=None, ppriority=None,
                      pto=None, ptype=None, pfrom=None, pnick=None):
        """
        Create and initialize a new
        :class:`~sleekxmpp.stanza.presence.Presence` stanza.

        :param pshow: The presence's show value.
        :param pstatus: The presence's status message.
        :param ppriority: This connection's priority.
        :param pto: The recipient of a directed presence.
        :param ptype: The type of presence, such as ``'subscribe'``.
        :param pfrom: The sender of the presence.
        :param pnick: Optional nickname of the presence's sender.
        """
        presence = self.Presence(stype=ptype, sfrom=pfrom, sto=pto)
        if pshow is not None:
            presence['type'] = pshow
        if pfrom is None and self.is_component:
            presence['from'] = self.boundjid.full
        presence['priority'] = ppriority
        presence['status'] = pstatus
        presence['nick'] = pnick
        return presence

    def send_message(self, mto, mbody, msubject=None, mtype=None,
                     mhtml=None, mfrom=None, mnick=None):
        """
        Create, initialize, and send a new
        :class:`~sleekxmpp.stanza.message.Message` stanza.

        :param mto: The recipient of the message.
        :param mbody: The main contents of the message.
        :param msubject: Optional subject for the message.
        :param mtype: The message's type, such as ``'chat'`` or
                      ``'groupchat'``.
        :param mhtml: Optional HTML body content in the form of a string.
        :param mfrom: The sender of the message. if sending from a client,
                      be aware that some servers require that the full JID
                      of the sender be used.
        :param mnick: Optional nickname of the sender.
        """
        self.make_message(mto, mbody, msubject, mtype,
                          mhtml, mfrom, mnick).send()

    def send_presence(self, pshow=None, pstatus=None, ppriority=None,
                      pto=None, pfrom=None, ptype=None, pnick=None):
        """
        Create, initialize, and send a new
        :class:`~sleekxmpp.stanza.presence.Presence` stanza.

        :param pshow: The presence's show value.
        :param pstatus: The presence's status message.
        :param ppriority: This connection's priority.
        :param pto: The recipient of a directed presence.
        :param ptype: The type of presence, such as ``'subscribe'``.
        :param pfrom: The sender of the presence.
        :param pnick: Optional nickname of the presence's sender.
        """
        self.make_presence(pshow, pstatus, ppriority, pto,
                           ptype, pfrom, pnick).send()

    def send_presence_subscription(self, pto, pfrom=None,
                                   ptype='subscribe', pnick=None):
        """
        Create, initialize, and send a new
        :class:`~sleekxmpp.stanza.presence.Presence` stanza of
        type ``'subscribe'``.

        :param pto: The recipient of a directed presence.
        :param pfrom: The sender of the presence.
        :param ptype: The type of presence, such as ``'subscribe'``.
        :param pnick: Optional nickname of the presence's sender.
        """
        self.make_presence(ptype=ptype,
                           pfrom=pfrom,
                           pto=JID(pto).bare,
                           pnick=pnick).send()

    @property
    def jid(self):
        """Attribute accessor for bare jid"""
        log.warning("jid property deprecated. Use boundjid.bare")
        return self.boundjid.bare

    @jid.setter
    def jid(self, value):
        log.warning("jid property deprecated. Use boundjid.bare")
        self.boundjid.bare = value

    @property
    def fulljid(self):
        """Attribute accessor for full jid"""
        log.warning("fulljid property deprecated. Use boundjid.full")
        return self.boundjid.full

    @fulljid.setter
    def fulljid(self, value):
        log.warning("fulljid property deprecated. Use boundjid.full")
        self.boundjid.full = value

    @property
    def resource(self):
        """Attribute accessor for jid resource"""
        log.warning("resource property deprecated. Use boundjid.resource")
        return self.boundjid.resource

    @resource.setter
    def resource(self, value):
        log.warning("fulljid property deprecated. Use boundjid.resource")
        self.boundjid.resource = value

    @property
    def username(self):
        """Attribute accessor for jid usernode"""
        log.warning("username property deprecated. Use boundjid.user")
        return self.boundjid.user

    @username.setter
    def username(self, value):
        log.warning("username property deprecated. Use boundjid.user")
        self.boundjid.user = value

    @property
    def server(self):
        """Attribute accessor for jid host"""
        log.warning("server property deprecated. Use boundjid.host")
        return self.boundjid.server

    @server.setter
    def server(self, value):
        log.warning("server property deprecated. Use boundjid.host")
        self.boundjid.server = value

    @property
    def auto_authorize(self):
        """Auto accept or deny subscription requests.

        If ``True``, auto accept subscription requests.
        If ``False``, auto deny subscription requests.
        If ``None``, don't automatically respond.
        """
        return self.roster.auto_authorize

    @auto_authorize.setter
    def auto_authorize(self, value):
        self.roster.auto_authorize = value

    @property
    def auto_subscribe(self):
        """Auto send requests for mutual subscriptions.

        If ``True``, auto send mutual subscription requests.
        """
        return self.roster.auto_subscribe

    @auto_subscribe.setter
    def auto_subscribe(self, value):
        self.roster.auto_subscribe = value

    def set_jid(self, jid):
        """Rip a JID apart and claim it as our own."""
        log.debug("setting jid to %s", jid)
        self.boundjid = JID(jid, cache_lock=True)

    def getjidresource(self, fulljid):
        if '/' in fulljid:
            return fulljid.split('/', 1)[-1]
        else:
            return ''

    def getjidbare(self, fulljid):
        return fulljid.split('/', 1)[0]

    def _handle_session_start(self, event):
        """Reset redirection attempt count."""
        self._redirect_attempts = 0

    def _handle_disconnected(self, event):
        """When disconnected, reset the roster"""
        self.roster.reset()
        self.session_bind_event.clear()

    def _handle_stream_error(self, error):
        self.event('stream_error', error)

        if error['condition'] == 'see-other-host':
            other_host = error['see_other_host']
            if not other_host:
                log.warning("No other host specified.")
                return

            if self._redirect_attempts > self.max_redirects:
                log.error("Exceeded maximum number of redirection attempts.")
                return

            self._redirect_attempts += 1

            host = other_host
            port = 5222

            if '[' in other_host and ']' in other_host:
                host = other_host.split(']')[0][1:]
            elif ':' in other_host:
                host = other_host.split(':')[0]

            port_sec = other_host.split(']')[-1]
            if ':' in port_sec:
                port = int(port_sec.split(':')[1])

            self.address = (host, port)
            self.default_domain = host
            self.dns_records = None
            self.reconnect_delay = None
            self.reconnect()

    def _handle_message(self, msg):
        """Process incoming message stanzas."""
        if not self.is_component and not msg['to'].bare:
            msg['to'] = self.boundjid
        self.event('message', msg)

    def _handle_available(self, pres):
        self.roster[pres['to']][pres['from']].handle_available(pres)

    def _handle_unavailable(self, pres):
        self.roster[pres['to']][pres['from']].handle_unavailable(pres)

    def _handle_new_subscription(self, pres):
        """Attempt to automatically handle subscription requests.

        Subscriptions will be approved if the request is from
        a whitelisted JID, of :attr:`auto_authorize` is True. They
        will be rejected if :attr:`auto_authorize` is False. Setting
        :attr:`auto_authorize` to ``None`` will disable automatic
        subscription handling (except for whitelisted JIDs).

        If a subscription is accepted, a request for a mutual
        subscription will be sent if :attr:`auto_subscribe` is ``True``.
        """
        roster = self.roster[pres['to']]
        item = self.roster[pres['to']][pres['from']]
        if item['whitelisted']:
            item.authorize()
            if roster.auto_subscribe:
                item.subscribe()
        elif roster.auto_authorize:
            item.authorize()
            if roster.auto_subscribe:
                item.subscribe()
        elif roster.auto_authorize == False:
            item.unauthorize()

    def _handle_removed_subscription(self, pres):
        self.roster[pres['to']][pres['from']].handle_unauthorize(pres)

    def _handle_subscribe(self, pres):
        self.roster[pres['to']][pres['from']].handle_subscribe(pres)

    def _handle_subscribed(self, pres):
        self.roster[pres['to']][pres['from']].handle_subscribed(pres)

    def _handle_unsubscribe(self, pres):
        self.roster[pres['to']][pres['from']].handle_unsubscribe(pres)

    def _handle_unsubscribed(self, pres):
        self.roster[pres['to']][pres['from']].handle_unsubscribed(pres)

    def _handle_presence(self, presence):
        """Process incoming presence stanzas.

        Update the roster with presence information.
        """
        if not self.is_component and not presence['to'].bare:
            presence['to'] = self.boundjid

        self.event('presence', presence)
        self.event('presence_%s' % presence['type'], presence)

        # Check for changes in subscription state.
        if presence['type'] in ('subscribe', 'subscribed',
                                'unsubscribe', 'unsubscribed'):
            self.event('changed_subscription', presence)
            return
        elif not presence['type'] in ('available', 'unavailable') and \
             not presence['type'] in presence.showtypes:
            return

    def exception(self, exception):
        """Process any uncaught exceptions, notably
        :class:`~sleekxmpp.exceptions.IqError` and
        :class:`~sleekxmpp.exceptions.IqTimeout` exceptions.

        :param exception: An unhandled :class:`Exception` object.
        """
        if isinstance(exception, IqError):
            iq = exception.iq
            log.error('%s: %s', iq['error']['condition'],
                                iq['error']['text'])
            log.warning('You should catch IqError exceptions')
        elif isinstance(exception, IqTimeout):
            iq = exception.iq
            log.error('Request timed out: %s', iq)
            log.warning('You should catch IqTimeout exceptions')
        elif isinstance(exception, SyntaxError):
            # Hide stream parsing errors that occur when the
            # stream is disconnected (they've been handled, we
            # don't need to make a mess in the logs).
            pass
        else:
            log.exception(exception)


# Restore the old, lowercased name for backwards compatibility.
basexmpp = BaseXMPP

# To comply with PEP8, method names now use underscores.
# Deprecated method names are re-mapped for backwards compatibility.
BaseXMPP.registerPlugin = BaseXMPP.register_plugin
BaseXMPP.makeIq = BaseXMPP.make_iq
BaseXMPP.makeIqGet = BaseXMPP.make_iq_get
BaseXMPP.makeIqResult = BaseXMPP.make_iq_result
BaseXMPP.makeIqSet = BaseXMPP.make_iq_set
BaseXMPP.makeIqError = BaseXMPP.make_iq_error
BaseXMPP.makeIqQuery = BaseXMPP.make_iq_query
BaseXMPP.makeQueryRoster = BaseXMPP.make_query_roster
BaseXMPP.makeMessage = BaseXMPP.make_message
BaseXMPP.makePresence = BaseXMPP.make_presence
BaseXMPP.sendMessage = BaseXMPP.send_message
BaseXMPP.sendPresence = BaseXMPP.send_presence
BaseXMPP.sendPresenceSubscription = BaseXMPP.send_presence_subscription
