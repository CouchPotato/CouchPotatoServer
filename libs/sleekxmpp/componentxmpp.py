# -*- coding: utf-8 -*-
"""
    sleekxmpp.clientxmpp
    ~~~~~~~~~~~~~~~~~~~~

    This module provides XMPP functionality that
    is specific to external server component connections.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from __future__ import absolute_import

import logging
import sys
import hashlib

from sleekxmpp.basexmpp import BaseXMPP
from sleekxmpp.xmlstream import XMLStream
from sleekxmpp.xmlstream import ET
from sleekxmpp.xmlstream.matcher import MatchXPath
from sleekxmpp.xmlstream.handler import Callback


log = logging.getLogger(__name__)


class ComponentXMPP(BaseXMPP):

    """
    SleekXMPP's basic XMPP server component.

    Use only for good, not for evil.

    :param jid: The JID of the component.
    :param secret: The secret or password for the component.
    :param host: The server accepting the component.
    :param port: The port used to connect to the server.
    :param plugin_config: A dictionary of plugin configurations.
    :param plugin_whitelist: A list of approved plugins that
                    will be loaded when calling
                    :meth:`~sleekxmpp.basexmpp.BaseXMPP.register_plugins()`.
    :param use_jc_ns: Indicates if the ``'jabber:client'`` namespace
                      should be used instead of the standard
                      ``'jabber:component:accept'`` namespace.
                      Defaults to ``False``.
    """

    def __init__(self, jid, secret, host=None, port=None,
                 plugin_config={}, plugin_whitelist=[], use_jc_ns=False):
        if use_jc_ns:
            default_ns = 'jabber:client'
        else:
            default_ns = 'jabber:component:accept'
        BaseXMPP.__init__(self, jid, default_ns)

        self.auto_authorize = None
        self.stream_header = "<stream:stream %s %s to='%s'>" % (
                'xmlns="jabber:component:accept"',
                'xmlns:stream="%s"' % self.stream_ns,
                jid)
        self.stream_footer = "</stream:stream>"
        self.server_host = host
        self.server_port = port
        self.secret = secret

        self.plugin_config = plugin_config
        self.plugin_whitelist = plugin_whitelist
        self.is_component = True

        self.register_handler(
                Callback('Handshake',
                         MatchXPath('{jabber:component:accept}handshake'),
                         self._handle_handshake))
        self.add_event_handler('presence_probe',
                               self._handle_probe)

    def connect(self, host=None, port=None, use_ssl=False,
                      use_tls=False, reattempt=True):
        """Connect to the server.

        Setting ``reattempt`` to ``True`` will cause connection attempts to
        be made every second until a successful connection is established.

        :param host: The name of the desired server for the connection.
                     Defaults to :attr:`server_host`.
        :param port: Port to connect to on the server.
                     Defauts to :attr:`server_port`.
        :param use_ssl: Flag indicating if SSL should be used by connecting
                        directly to a port using SSL.
        :param use_tls: Flag indicating if TLS should be used, allowing for
                        connecting to a port without using SSL immediately and
                        later upgrading the connection.
        :param reattempt: Flag indicating if the socket should reconnect
                          after disconnections.
        """
        if host is None:
            host = self.server_host
        if port is None:
            port = self.server_port

        self.server_name = self.boundjid.host

        if use_tls:
            log.info("XEP-0114 components can not use TLS")

        log.debug("Connecting to %s:%s", host, port)
        return XMLStream.connect(self, host=host, port=port,
                                       use_ssl=use_ssl,
                                       use_tls=False,
                                       reattempt=reattempt)

    def incoming_filter(self, xml):
        """
        Pre-process incoming XML stanzas by converting any
        ``'jabber:client'`` namespaced elements to the component's
        default namespace.

        :param xml: The XML stanza to pre-process.
        """
        if xml.tag.startswith('{jabber:client}'):
            xml.tag = xml.tag.replace('jabber:client', self.default_ns)

        # The incoming_filter call is only made on top level stanza
        # elements. So we manually continue filtering on sub-elements.
        for sub in xml:
            self.incoming_filter(sub)

        return xml

    def start_stream_handler(self, xml):
        """
        Once the streams are established, attempt to handshake
        with the server to be accepted as a component.

        :param xml: The incoming stream's root element.
        """
        BaseXMPP.start_stream_handler(self, xml)

        # Construct a hash of the stream ID and the component secret.
        sid = xml.get('id', '')
        pre_hash = '%s%s' % (sid, self.secret)
        if sys.version_info >= (3, 0):
            # Handle Unicode byte encoding in Python 3.
            pre_hash = bytes(pre_hash, 'utf-8')

        handshake = ET.Element('{jabber:component:accept}handshake')
        handshake.text = hashlib.sha1(pre_hash).hexdigest().lower()
        self.send_xml(handshake, now=True)

    def _handle_handshake(self, xml):
        """The handshake has been accepted.

        :param xml: The reply handshake stanza.
        """
        self.session_bind_event.set()
        self.session_started_event.set()
        self.event("session_bind", self.boundjid, direct=True)
        self.event("session_start")

    def _handle_probe(self, pres):
        self.roster[pres['to']][pres['from']].handle_probe(pres)
