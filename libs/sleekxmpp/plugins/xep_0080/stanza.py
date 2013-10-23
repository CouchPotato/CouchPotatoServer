"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

from sleekxmpp.xmlstream import ElementBase
from sleekxmpp.plugins import xep_0082


class Geoloc(ElementBase):

    """
    XMPP's <geoloc> stanza allows entities to know the current
    geographical or physical location of an entity. (XEP-0080: User Location)

    Example <geoloc> stanzas:
        <geoloc xmlns='http://jabber.org/protocol/geoloc'/>

        <geoloc xmlns='http://jabber.org/protocol/geoloc' xml:lang='en'>
          <accuracy>20</accuracy>
          <country>Italy</country>
          <lat>45.44</lat>
          <locality>Venice</locality>
          <lon>12.33</lon>
        </geoloc>

    Stanza Interface:
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
    """

    namespace = 'http://jabber.org/protocol/geoloc'
    name = 'geoloc'
    interfaces = set(('accuracy', 'alt', 'area', 'bearing', 'building',
                      'country', 'countrycode', 'datum', 'dscription',
                      'error', 'floor', 'lat', 'locality', 'lon',
                      'postalcode', 'region', 'room', 'speed', 'street',
                      'text', 'timestamp', 'uri'))
    sub_interfaces = interfaces
    plugin_attrib = name

    def exception(self, e):
        """
        Override exception passback for presence.
        """
        pass

    def set_accuracy(self, accuracy):
        """
        Set the value of the <accuracy> element.

        Arguments:
            accuracy -- Horizontal GPS error in meters
        """
        self._set_sub_text('accuracy', text=str(accuracy))
        return self

    def get_accuracy(self):
        """
        Return the value of the <accuracy> element as an integer.
        """
        p = self._get_sub_text('accuracy')
        if not p:
            return None
        else:
            try:
                return int(p)
            except ValueError:
                return None

    def set_alt(self, alt):
        """
        Set the value of the <alt> element.

        Arguments:
            alt -- Altitude in meters above or below sea level
        """
        self._set_sub_text('alt', text=str(alt))
        return self

    def get_alt(self):
        """
        Return the value of the <alt> element as an integer.
        """
        p = self._get_sub_text('alt')
        if not p:
            return None
        else:
            try:
                return int(p)
            except ValueError:
                return None

    def set_bearing(self, bearing):
        """
        Set the value of the <bearing> element.

        Arguments:
            bearing -- GPS bearing (direction in which the entity is heading
                       to reach its next waypoint), measured in decimal
                       degrees relative to true north
        """
        self._set_sub_text('bearing', text=str(bearing))
        return self

    def get_bearing(self):
        """
        Return the value of the <bearing> element as a float.
        """
        p = self._get_sub_text('bearing')
        if not p:
            return None
        else:
            try:
                return float(p)
            except ValueError:
                return None

    def set_error(self, error):
        """
        Set the value of the <error> element.

        Arguments:
            error -- Horizontal GPS error in arc minutes; this
                     element is deprecated in favor of <accuracy/>
        """
        self._set_sub_text('error', text=str(error))
        return self

    def get_error(self):
        """
        Return the value of the <error> element as a float.
        """
        p = self._get_sub_text('error')
        if not p:
            return None
        else:
            try:
                return float(p)
            except ValueError:
                return None

    def set_lat(self, lat):
        """
        Set the value of the <lat> element.

        Arguments:
            lat -- Latitude in decimal degrees North
        """
        self._set_sub_text('lat', text=str(lat))
        return self

    def get_lat(self):
        """
        Return the value of the <lat> element as a float.
        """
        p = self._get_sub_text('lat')
        if not p:
            return None
        else:
            try:
                return float(p)
            except ValueError:
                return None

    def set_lon(self, lon):
        """
        Set the value of the <lon> element.

        Arguments:
            lon -- Longitude in decimal degrees East
        """
        self._set_sub_text('lon', text=str(lon))
        return self

    def get_lon(self):
        """
        Return the value of the <lon> element as a float.
        """
        p = self._get_sub_text('lon')
        if not p:
            return None
        else:
            try:
                return float(p)
            except ValueError:
                return None

    def set_speed(self, speed):
        """
        Set the value of the <speed> element.

        Arguments:
            speed -- The speed at which the entity is moving,
                     in meters per second
        """
        self._set_sub_text('speed', text=str(speed))
        return self

    def get_speed(self):
        """
        Return the value of the <speed> element as a float.
        """
        p = self._get_sub_text('speed')
        if not p:
            return None
        else:
            try:
                return float(p)
            except ValueError:
                return None

    def set_timestamp(self, timestamp):
        """
        Set the value of the <timestamp> element.

        Arguments:
            timestamp -- UTC timestamp specifying the moment when
                         the reading was taken
        """
        self._set_sub_text('timestamp', text=str(xep_0082.datetime(timestamp)))
        return self

    def get_timestamp(self):
        """
        Return the value of the <timestamp> element as a DateTime.
        """
        p = self._get_sub_text('timestamp')
        if not p:
            return None
        else:
            return xep_0082.datetime(p)
