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
from sleekxmpp.plugins.xep_0313 import stanza


log = logging.getLogger(__name__)


class XEP_0313(BasePlugin):

    """
    XEP-0313 Message Archive Management
    """

    name = 'xep_0313'
    description = 'XEP-0313: Message Archive Management'
    dependencies = set(['xep_0030', 'xep_0050', 'xep_0059', 'xep_0297'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, stanza.MAM)
        register_stanza_plugin(Iq, stanza.Preferences)
        register_stanza_plugin(Message, stanza.Result)
        register_stanza_plugin(stanza.MAM, self.xmpp['xep_0059'].stanza.Set)

    def retrieve(self, jid=None, start=None, end=None, with_jid=None, ifrom=None,
                 block=True, timeout=None, callback=None, iterator=False):
        iq = self.xmpp.Iq()
        query_id = iq['id']

        iq['to'] = jid
        iq['from'] = ifrom
        iq['type'] = 'get'
        iq['mam']['queryid'] = query_id
        iq['mam']['start'] = start
        iq['mam']['end'] = end
        iq['mam']['with'] = with_jid

        collector = Collector(
            'MAM_Results_%s' % query_id,
            StanzaPath('message/mam_result@queryid=%s' % query_id))
        self.xmpp.register_handler(collector)

        if iterator:
            return self.xmpp['xep_0059'].iterate(iq, 'mam', 'results')
        elif not block and callback is not None:
            def wrapped_cb(iq):
                results = collector.stop()
                if iq['type'] == 'result':
                    iq['mam']['results'] = results
                callback(iq)
            return iq.send(block=block, timeout=timeout, callback=wrapped_cb)
        else:
            try:
                resp = iq.send(block=block, timeout=timeout, callback=callback)
                resp['mam']['results'] = collector.stop()
                return resp
            except XMPPError as e:
                collector.stop()
                raise e

    def set_preferences(self, jid=None, default=None, always=None, never=None,
                        ifrom=None, block=True, timeout=None, callback=None):
        iq = self.xmpp.Iq()
        iq['type'] = 'set'
        iq['to'] = jid
        iq['from'] = ifrom
        iq['mam_prefs']['default'] = default
        iq['mam_prefs']['always'] = always
        iq['mam_prefs']['never'] = never
        return iq.send(block=block, timeout=timeout, callback=callback)

    def get_configuration_commands(self, jid, **kwargs):
        return self.xmpp['xep_0030'].get_items(
                jid=jid,
                node='urn:xmpp:mam#configure',
                **kwargs)
