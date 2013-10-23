"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2011 Nathanael C. Fritz, Lance J.T. Stout
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import logging
import datetime as dt

from sleekxmpp.plugins import BasePlugin, register_plugin
from sleekxmpp.thirdparty import tzutc, tzoffset, parse_iso


# =====================================================================
# To make it easier for stanzas without direct access to plugin objects
# to use the XEP-0082 utility methods, we will define them as top-level
# functions and then just reference them in the plugin itself.

def parse(time_str):
    """
    Convert a string timestamp into a datetime object.

    Arguments:
        time_str -- A formatted timestamp string.
    """
    return parse_iso(time_str)


def format_date(time_obj):
    """
    Return a formatted string version of a date object.

    Format:
        YYYY-MM-DD

    Arguments:
        time_obj -- A date or datetime object.
    """
    if isinstance(time_obj, dt.datetime):
        time_obj = time_obj.date()
    return time_obj.isoformat()


def format_time(time_obj):
    """
    Return a formatted string version of a time object.

    format:
        hh:mm:ss[.sss][TZD]

    arguments:
        time_obj -- A time or datetime object.
    """
    if isinstance(time_obj, dt.datetime):
        time_obj = time_obj.timetz()
    timestamp = time_obj.isoformat()
    if time_obj.tzinfo == tzutc():
        timestamp = timestamp[:-6]
        return '%sZ' % timestamp
    return timestamp


def format_datetime(time_obj):
    """
    Return a formatted string version of a datetime object.

    Format:
        YYYY-MM-DDThh:mm:ss[.sss]TZD

    arguments:
        time_obj -- A datetime object.
    """
    timestamp = time_obj.isoformat('T')
    if time_obj.tzinfo == tzutc():
        timestamp = timestamp[:-6]
        return '%sZ' % timestamp
    return timestamp


def date(year=None, month=None, day=None, obj=False):
    """
    Create a date only timestamp for the given instant.

    Unspecified components default to their current counterparts.

    Arguments:
        year   -- Integer value of the year (4 digits)
        month  -- Integer value of the month
        day    -- Integer value of the day of the month.
        obj    -- If True, return the date object instead
                  of a formatted string. Defaults to False.
    """
    today = dt.datetime.utcnow()
    if year is None:
        year = today.year
    if month is None:
        month = today.month
    if day is None:
        day = today.day
    value = dt.date(year, month, day)
    if obj:
        return value
    return format_date(value)


def time(hour=None, min=None, sec=None, micro=None, offset=None, obj=False):
    """
    Create a time only timestamp for the given instant.

    Unspecified components default to their current counterparts.

    Arguments:
        hour   -- Integer value of the hour.
        min    -- Integer value of the number of minutes.
        sec    -- Integer value of the number of seconds.
        micro  -- Integer value of the number of microseconds.
        offset -- Either a positive or negative number of seconds
                  to offset from UTC to match a desired timezone,
                  or a tzinfo object.
        obj    -- If True, return the time object instead
                  of a formatted string. Defaults to False.
    """
    now = dt.datetime.utcnow()
    if hour is None:
        hour = now.hour
    if min is None:
        min = now.minute
    if sec is None:
        sec = now.second
    if micro is None:
        micro = now.microsecond
    if offset is None:
        offset = tzutc()
    elif not isinstance(offset, dt.tzinfo):
        offset = tzoffset(None, offset)
    value = dt.time(hour, min, sec, micro, offset)
    if obj:
        return value
    return format_time(value)


def datetime(year=None, month=None, day=None, hour=None,
             min=None, sec=None, micro=None, offset=None,
             separators=True, obj=False):
    """
    Create a datetime timestamp for the given instant.

    Unspecified components default to their current counterparts.

    Arguments:
        year   -- Integer value of the year (4 digits)
        month  -- Integer value of the month
        day    -- Integer value of the day of the month.
        hour   -- Integer value of the hour.
        min    -- Integer value of the number of minutes.
        sec    -- Integer value of the number of seconds.
        micro  -- Integer value of the number of microseconds.
        offset -- Either a positive or negative number of seconds
                  to offset from UTC to match a desired timezone,
                  or a tzinfo object.
        obj    -- If True, return the datetime object instead
                  of a formatted string. Defaults to False.
    """
    now = dt.datetime.utcnow()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    if day is None:
        day = now.day
    if hour is None:
        hour = now.hour
    if min is None:
        min = now.minute
    if sec is None:
        sec = now.second
    if micro is None:
        micro = now.microsecond
    if offset is None:
        offset = tzutc()
    elif not isinstance(offset, dt.tzinfo):
        offset = tzoffset(None, offset)

    value = dt.datetime(year, month, day, hour,
                       min, sec, micro, offset)
    if obj:
        return value
    return format_datetime(value)


class XEP_0082(BasePlugin):

    """
    XEP-0082: XMPP Date and Time Profiles

    XMPP uses a subset of the formats allowed by ISO 8601 as a matter of
    pragmatism based on the relatively few formats historically used by
    the XMPP.

    Also see <http://www.xmpp.org/extensions/xep-0082.html>.

    Methods:
        date            -- Create a time stamp using the Date profile.
        datetime        -- Create a time stamp using the DateTime profile.
        time            -- Create a time stamp using the Time profile.
        format_date     -- Format an existing date object.
        format_datetime -- Format an existing datetime object.
        format_time     -- Format an existing time object.
        parse           -- Convert a time string into a Python datetime object.
    """

    name = 'xep_0082'
    description = 'XEP-0082: XMPP Date and Time Profiles'
    dependencies = set()

    def plugin_init(self):
        """Start the XEP-0082 plugin."""
        self.date = date
        self.datetime = datetime
        self.time = time
        self.format_date = format_date
        self.format_datetime = format_datetime
        self.format_time = format_time
        self.parse = parse


register_plugin(XEP_0082)
