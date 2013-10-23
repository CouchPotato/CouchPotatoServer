"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2012 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging
from datetime import datetime, timedelta

from sleekxmpp.plugins import BasePlugin, register_plugin
from sleekxmpp import Iq
from sleekxmpp.exceptions import XMPPError
from sleekxmpp.xmlstream import JID, register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.plugins.xep_0012 import stanza, LastActivity


log = logging.getLogger(__name__)


class XEP_0012(BasePlugin):

    """
    XEP-0012 Last Activity
    """

    name = 'xep_0012'
    description = 'XEP-0012: Last Activity'
    dependencies = set(['xep_0030'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Iq, LastActivity)

        self._last_activities = {}

        self.xmpp.register_handler(
            Callback('Last Activity',
                 StanzaPath('iq@type=get/last_activity'),
                 self._handle_get_last_activity))

        self.api.register(self._default_get_last_activity,
                'get_last_activity',
                default=True)
        self.api.register(self._default_set_last_activity,
                'set_last_activity',
                default=True)
        self.api.register(self._default_del_last_activity,
                'del_last_activity',
                default=True)

    def plugin_end(self):
        self.xmpp.remove_handler('Last Activity')
        self.xmpp['xep_0030'].del_feature(feature='jabber:iq:last')

    def session_bind(self, jid):
        self.xmpp['xep_0030'].add_feature('jabber:iq:last')

    def begin_idle(self, jid=None, status=None):
        self.set_last_activity(jid, 0, status)

    def end_idle(self, jid=None):
        self.del_last_activity(jid)

    def start_uptime(self, status=None):
        self.set_last_activity(jid, 0, status)

    def set_last_activity(self, jid=None, seconds=None, status=None):
        self.api['set_last_activity'](jid, args={
            'seconds': seconds,
            'status': status})

    def del_last_activity(self, jid):
        self.api['del_last_activity'](jid)

    def get_last_activity(self, jid, local=False, ifrom=None, block=True,
                          timeout=None, callback=None):
        if jid is not None and not isinstance(jid, JID):
            jid = JID(jid)

        if self.xmpp.is_component:
            if jid.domain == self.xmpp.boundjid.domain:
                local = True
        else:
            if str(jid) == str(self.xmpp.boundjid):
                local = True
        jid = jid.full

        if local or jid in (None, ''):
            log.debug("Looking up local last activity data for %s", jid)
            return self.api['get_last_activity'](jid, None, ifrom, None)

        iq = self.xmpp.Iq()
        iq['from'] = ifrom
        iq['to'] = jid
        iq['type'] = 'get'
        iq.enable('last_activity')
        return iq.send(timeout=timeout,
                       block=block,
                       callback=callback)

    def _handle_get_last_activity(self, iq):
        log.debug("Received last activity query from " + \
                  "<%s> to <%s>.", iq['from'], iq['to'])
        reply = self.api['get_last_activity'](iq['to'], None, iq['from'], iq)
        reply.send()

    # =================================================================
    # Default in-memory implementations for storing last activity data.
    # =================================================================

    def _default_set_last_activity(self, jid, node, ifrom, data):
        seconds = data.get('seconds', None)
        if seconds is None:
            seconds = 0

        status = data.get('status', None)
        if status is None:
            status = ''

        self._last_activities[jid] = {
            'seconds': datetime.now() - timedelta(seconds=seconds),
            'status': status}

    def _default_del_last_activity(self, jid, node, ifrom, data):
        if jid in self._last_activities:
            del self._last_activities[jid]

    def _default_get_last_activity(self, jid, node, ifrom, iq):
        if not isinstance(iq, Iq):
            reply = self.xmpp.Iq()
        else:
            iq.reply()
            reply = iq

        if jid not in self._last_activities:
            raise XMPPError('service-unavailable')

        bare = JID(jid).bare

        if bare != self.xmpp.boundjid.bare:
            if bare in self.xmpp.roster[jid]:
                sub = self.xmpp.roster[jid][bare]['subscription']
                if sub not in ('from', 'both'):
                    raise XMPPError('forbidden')

        td = datetime.now() - self._last_activities[jid]['seconds']
        seconds = td.seconds + td.days * 24 * 3600
        status = self._last_activities[jid]['status']

        reply['last_activity']['seconds'] = seconds
        reply['last_activity']['status'] = status

        return reply
