"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

from sleekxmpp.plugins.base import BasePlugin
from sleekxmpp.plugins.xep_0118 import stanza, UserTune


log = logging.getLogger(__name__)


class XEP_0118(BasePlugin):

    """
    XEP-0118: User Tune
    """

    name = 'xep_0118'
    description = 'XEP-0118: User Tune'
    dependencies = set(['xep_0163'])
    stanza = stanza

    def plugin_end(self):
        self.xmpp['xep_0030'].del_feature(feature=UserTune.namespace)
        self.xmpp['xep_0163'].remove_interest(UserTune.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0163'].register_pep('user_tune', UserTune)

    def publish_tune(self, artist=None, length=None, rating=None, source=None,
                     title=None, track=None, uri=None, options=None,
                     ifrom=None, block=True, callback=None, timeout=None):
        """
        Publish the user's current tune.

        Arguments:
            artist   -- The artist or performer of the song.
            length   -- The length of the song in seconds.
            rating   -- The user's rating of the song (from 1 to 10)
            source   -- The album name, website, or other source of the song.
            title    -- The title of the song.
            track    -- The song's track number, or other unique identifier.
            uri      -- A URL to more information about the song.
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
        tune = UserTune()
        tune['artist'] = artist
        tune['length'] = length
        tune['rating'] = rating
        tune['source'] = source
        tune['title'] = title
        tune['track'] = track
        tune['uri'] = uri
        return self.xmpp['xep_0163'].publish(tune,
                node=UserTune.namespace,
                options=options,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)

    def stop(self, ifrom=None, block=True, callback=None, timeout=None):
        """
        Clear existing user tune information to stop notifications.

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
        tune = UserTune()
        return self.xmpp['xep_0163'].publish(tune,
                node=UserTune.namespace,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)
