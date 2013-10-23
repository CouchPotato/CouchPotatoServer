"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010 Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging
import datetime as dt

from sleekxmpp.xmlstream import ElementBase
from sleekxmpp.plugins import xep_0082
from sleekxmpp.thirdparty import tzutc, tzoffset


class EntityTime(ElementBase):

    """
    The <time> element represents the local time for an XMPP agent.
    The time is expressed in UTC to make synchronization easier
    between entities, but the offset for the local timezone is also
    included.

    Example <time> stanzas:
        <iq type="result">
          <time xmlns="urn:xmpp:time">
            <utc>2011-07-03T11:37:12.234569</utc>
            <tzo>-07:00</tzo>
          </time>
        </iq>

    Stanza Interface:
        time -- The local time for the entity (updates utc and tzo).
        utc  -- The UTC equivalent to local time.
        tzo  -- The local timezone offset from UTC.

    Methods:
        get_time -- Return local time datetime object.
        set_time -- Set UTC and TZO fields.
        del_time -- Remove both UTC and TZO fields.
        get_utc  -- Return datetime object of UTC time.
        set_utc  -- Set the UTC time.
        get_tzo  -- Return tzinfo object.
        set_tzo  -- Set the local timezone offset.
    """

    name = 'time'
    namespace = 'urn:xmpp:time'
    plugin_attrib = 'entity_time'
    interfaces = set(('tzo', 'utc', 'time'))
    sub_interfaces = interfaces

    def set_time(self, value):
        """
        Set both the UTC and TZO fields given a time object.

        Arguments:
            value -- A datetime object or properly formatted
                     string equivalent.
        """
        date = value
        if not isinstance(value, dt.datetime):
            date = xep_0082.parse(value)
        self['utc'] = date
        self['tzo'] = date.tzinfo

    def get_time(self):
        """
        Return the entity's local time based on the UTC and TZO data.
        """
        date = self['utc']
        tz = self['tzo']
        return date.astimezone(tz)

    def del_time(self):
        """Remove both the UTC and TZO fields."""
        del self['utc']
        del self['tzo']

    def get_tzo(self):
        """
        Return the timezone offset from UTC as a tzinfo object.
        """
        tzo = self._get_sub_text('tzo')
        if tzo == '':
            tzo = 'Z'
        time = xep_0082.parse('00:00:00%s' % tzo)
        return time.tzinfo

    def set_tzo(self, value):
        """
        Set the timezone offset from UTC.

        Arguments:
            value -- Either a tzinfo object or the number of
                     seconds (positive or negative) to offset.
        """
        time = xep_0082.time(offset=value)
        if xep_0082.parse(time).tzinfo == tzutc():
            self._set_sub_text('tzo', 'Z')
        else:
            self._set_sub_text('tzo', time[-6:])

    def get_utc(self):
        """
        Return the time in UTC as a datetime object.
        """
        value = self._get_sub_text('utc')
        if value == '':
            return xep_0082.parse(xep_0082.datetime())
        return xep_0082.parse('%sZ' % value)

    def set_utc(self, value):
        """
        Set the time in UTC.

        Arguments:
            value -- A datetime object or properly formatted
                     string equivalent.
        """
        date = value
        if not isinstance(value, dt.datetime):
            date = xep_0082.parse(value)
        date = date.astimezone(tzutc())
        value = xep_0082.format_datetime(date)[:-1]
        self._set_sub_text('utc', value)
