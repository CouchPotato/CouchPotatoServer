"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz, Erik Reuterborg Larsson
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging

import sleekxmpp
from sleekxmpp.plugins.base import BasePlugin
from sleekxmpp.xmlstream import register_stanza_plugin
from sleekxmpp.plugins.xep_0080 import stanza, Geoloc


log = logging.getLogger(__name__)


class XEP_0080(BasePlugin):

    """
    XEP-0080: User Location
    """

    name = 'xep_0080'
    description = 'XEP-0080: User Location'
    dependencies = set(['xep_0163'])
    stanza = stanza

    def plugin_end(self):
        self.xmpp['xep_0163'].remove_interest(Geoloc.namespace)
        self.xmpp['xep_0030'].del_feature(feature=Geoloc.namespace)

    def session_bind(self, jid):
        self.xmpp['xep_0163'].register_pep('user_location', Geoloc)

    def publish_location(self, **kwargs):
        """
        Publish the user's current location.

        Arguments:
            accuracy    -- Horizontal GPS error in meters.
            alt         -- Altitude in meters above or below sea level.
            area        -- A named area such as a campus or neighborhood.
            bearing     -- GPS bearing (direction in which the entity is
                           heading to reach its next waypoint), measured in
                           decimal degrees relative to true north.
            building    -- A specific building on a street or in an area.
            country     -- The nation where the user is located.
            countrycode -- The ISO 3166 two-letter country code.
            datum       -- GPS datum.
            description -- A natural-language name for or description of
                           the location.
            error       -- Horizontal GPS error in arc minutes. Obsoleted by
                           the accuracy parameter.
            floor       -- A particular floor in a building.
            lat         -- Latitude in decimal degrees North.
            locality    -- A locality within the administrative region, such
                           as a town or city.
            lon         -- Longitude in decimal degrees East.
            postalcode  -- A code used for postal delivery.
            region      -- An administrative region of the nation, such
                           as a state or province.
            room        -- A particular room in a building.
            speed       -- The speed at which the entity is moving,
                           in meters per second.
            street      -- A thoroughfare within the locality, or a crossing
                           of two thoroughfares.
            text        -- A catch-all element that captures any other
                           information about the location.
            timestamp   -- UTC timestamp specifying the moment when the
                           reading was taken.
            uri         -- A URI or URL pointing to information about
                           the location.

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
        options = kwargs.get('options', None)
        ifrom = kwargs.get('ifrom', None)
        block = kwargs.get('block', None)
        callback = kwargs.get('callback', None)
        timeout = kwargs.get('timeout', None)
        for param in ('ifrom', 'block', 'callback', 'timeout', 'options'):
            if param in kwargs:
                del kwargs[param]

        geoloc = Geoloc()
        geoloc.values = kwargs

        return self.xmpp['xep_0163'].publish(geoloc,
                options=options,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)

    def stop(self, ifrom=None, block=True, callback=None, timeout=None):
        """
        Clear existing user location information to stop notifications.

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
        geoloc = Geoloc()
        return self.xmpp['xep_0163'].publish(geoloc,
                ifrom=ifrom,
                block=block,
                callback=callback,
                timeout=timeout)
