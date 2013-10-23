"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permissio
"""

import logging

import sleekxmpp
from sleekxmpp.stanza import Message, Iq
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.xmlstream.handler import Collector
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins import BasePlugin
from sleekxmpp.plugins.xep_0013 import stanza


log = logging.getLogger(__name__)


class XEP_0013(BasePlugin):

    """
    XEP-0013 Flexible Offline Message Retrieval
    """

    name = 'xep_0013'
    description = 'XEP-0013: Flexible Offline Message Retrieval'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, stanza.Offline)
        register_stanza_plugin(Message, stanza.Offline)

    def get_count(self, **kwargs):
        return self.xmpp['xep_0030'].get_info(
                node='http://jabber.org/protocol/offline',
                local=False,
                **kwargs)

    def get_headers(self, **kwargs):
        return self.xmpp['xep_0030'].get_items(
                node='http://jabber.org/protocol/offline',
                local=False,
                **kwargs)

    def view(self, nodes, ifrom=None, block=True, timeout=None, callback=None):
        if not isinstance(nodes, (list, set)):
            nodes = [nodes]

        iq = self.xmpp.Iq()
        iq['type'] = 'get'
        iq['from'] = ifrom
        offline = iq['offline']
        for node in nodes:
            item = stanza.Item()
            item['node'] = node
            item['action'] = 'view'
            offline.append(item)

        collector = Collector(
            'Offline_Results_%s' % iq['id'],
            StanzaPath('message/offline'))
        self.xmpp.register_handler(collector)

        if not block and callback is not None:
            def wrapped_cb(iq):
                results = collector.stop()
                if iq['type'] == 'result':
                    iq['offline']['results'] = results
                callback(iq)
            return iq.send(block=block, timeout=timeout, callback=wrapped_cb)
        else:
            try:
                resp = iq.send(block=block, timeout=timeout, callback=callback)
                resp['offline']['results'] = collector.stop()
                return resp
            except XMPPError as e:
                collector.stop()
                raise e

    def remove(self, nodes, ifrom=None, block=True, timeout=None, callback=None):
        if not isinstance(nodes, (list, set)):
            nodes = [nodes]

        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        offline = iq['offline']
        for node in nodes:
            item = stanza.Item()
            item['node'] = node
            item['action'] = 'remove'
            offline.append(item)

        return iq.send(block=block, timeout=timeout, callback=callback)

    def fetch(self, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['offline']['fetch'] = True

        collector = Collector(
            'Offline_Results_%s' % iq['id'],
            StanzaPath('message/offline'))
        self.xmpp.register_handler(collector)

        if not block and callback is not None:
            def wrapped_cb(iq):
                results = collector.stop()
                if iq['type'] == 'result':
                    iq['offline']['results'] = results
                callback(iq)
            return iq.send(block=block, timeout=timeout, callback=wrapped_cb)
        else:
            try:
                resp = iq.send(block=block, timeout=timeout, callback=callback)
                resp['offline']['results'] = collector.stop()
                return resp
            except XMPPError as e:
                collector.stop()
                raise e

    def purge(self, ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['from'] = ifrom
        iq['offline']['purge'] = True
        return iq.send(block=block, timeout=timeout, callback=callback)
