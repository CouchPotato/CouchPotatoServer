"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.stanza.message import Message
from sleekxmpp.stanza.presence import Presence
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import MatchXPath
from sleekxmpp.plugins.base import BasePlugin
from sleekxmpp.plugins.xep_0172 import stanza, UserNick


log = logging.getLogger(__name__)


class XEP_0172(BasePlugin):

    """
    XEP-0172: User Nickname
    """

    name = 'xep_0172'
    description = 'XEP-0172: User Nickname'
    dependencies = set(['xep_0163'])
    stanza = stanza

    def plugin_init(self):
        register_stanza_plugin(Message, UserNick)
        register_stanza_plugin(Presence, UserNick)

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature=UserNick.namespace)
        self.xmpp['xep_0163'].remove_interest(UserNick.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0163'].register_pep('user_nick', UserNick)

    def publish_nick(self, nick=None, options=None, ifrom=None, block=True,
                     callback=None, timeout=None):
        """
        Publish the user's current nick.

        Arguments:
            nick     -- The user nickname to publish.
            options  -- Optional form of publish options.
            ifrom    -- Specify the sender's JID.
            block    -- Specify if the send call will block until a response
                        is received, or a timeout occurs. Defaults to True.
            timeout  -- The length of time (in seconds) to wait for a response
                        before exiting the send call if blocking is used.
                        Defaults to sleekxmpp.xmlstream.RESPONSE_TIMEOUT
            callback -- Optional reference to a stream handler function. Will
                        be executed when a reply stanza is received.
        """
        nickname = UserNick()
        nickname['nick'] = nick
        return self.xmpp['xep_0163'].publish(nickname,
                node=UserNick.namespace,
                options=options,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)

    def stop(self, ifrom=None, block=True, callback=None, timeout=None):
        """
        Clear existing user nick information to stop notifications.

        Arguments:
            ifrom    -- Specify the sender's JID.
            block    -- Specify if the send call will block until a response
                        is received, or a timeout occurs. Defaults to True.
            timeout  -- The length of time (in seconds) to wait for a response
                        before exiting the send call if blocking is used.
                        Defaults to sleekxmpp.xmlstream.RESPONSE_TIMEOUT
            callback -- Optional reference to a stream handler function. Will
                        be executed when a reply stanza is received.
        """
        nick = UserNick()
        return self.xmpp['xep_0163'].publish(nick,
                node=UserNick.namespace,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)
