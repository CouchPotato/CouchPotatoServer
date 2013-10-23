# This module is a very stripped down version of the dateutil
# package for when dateutil has not been installed. As a replacement
# for dateutil.parser.parse, the parsing methods from
# http://blog.mfabrik.com/2008/06/30/relativity-of-time-shortcomings-in-python-datetime-and-workaround/

#As such, the following copyrights and licenses applies:


# dateutil - Extensions to the standard python 2.3+ datetime module.
#
# Copyright (c) 2003-2011 - Gustavo Niemeyer <gustavo@niemeyer.net>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


# fixed_dateime
#
# Copyright (c) 2008, Red Innovation Ltd., Finland
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Red Innovation nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY RED INNOVATION ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL RED INNOVATION BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



import re
import math
import datetime


ZERO = datetime.timedelta(0)


try:
    from dateutil.parser import parse as parse_iso
    from dateutil.tz import tzoffset, tzutc
except:
    # As a stopgap, define the two timezones here based
    # on the dateutil code.

    class tzutc(datetime.tzinfo):

        def utcoffset(self, dt):
            return ZERO

        def dst(self, dt):
            return ZERO

        def tzname(self, dt):
            return "UTC"

        def __eq__(self, other):
            return (isinstance(other, tzutc) or
                    (isinstance(other, tzoffset) and other._offset == ZERO))

        def __ne__(self, other):
            return not self.__eq__(other)

        def __repr__(self):
            return "%s()" % self.__class__.__name__

        __reduce__ = object.__reduce__

    class tzoffset(datetime.tzinfo):

        def __init__(self, name, offset):
            self._name = name
            self._offset = datetime.timedelta(seconds=offset)

        def utcoffset(self, dt):
            return self._offset

        def dst(self, dt):
            return ZERO

        def tzname(self, dt):
            return self._name

        def __eq__(self, other):
            return (isinstance(other, tzoffset) and
                    self._offset == other._offset)

        def __ne__(self, other):
            return not self.__eq__(other)

        def __repr__(self):
            return "%s(%s, %s)" % (self.__class__.__name__,
                                   repr(self._name),
                                   self._offset.days*86400+self._offset.seconds)

        __reduce__ = object.__reduce__


    _fixed_offset_tzs = { }
    UTC = tzutc()

    def _get_fixed_offset_tz(offsetmins):
        """For internal use only: Returns a tzinfo with
        the given fixed offset. This creates only one instance
        for each offset; the zones are kept in a dictionary"""

        if offsetmins == 0:
            return UTC

        if not offsetmins in _fixed_offset_tzs:
            if offsetmins < 0:
                sign = '-'
                absoff = -offsetmins
            else:
                sign = '+'
                absoff = offsetmins

            name = "UTC%s%02d:%02d" % (sign, int(absoff / 60), absoff % 60)
            inst = tzoffset(offsetmins, name)
            _fixed_offset_tzs[offsetmins] = inst

        return _fixed_offset_tzs[offsetmins]


    _iso8601_parser = re.compile("""
        ^
        (?P<year> [0-9]{4})?(?P<ymdsep>-?)?
        (?P<month>[0-9]{2})?(?P=ymdsep)?
        (?P<day>  [0-9]{2})?

        (?P<time>
            (?: # time part... optional... at least hour must be specified
            (?:T|\s+)?
                (?P<hour>[0-9]{2})
                (?:
                    # minutes, separated with :, or none, from hours
                    (?P<hmssep>[:]?)
                    (?P<minute>[0-9]{2})
                    (?:
                        # same for seconds, separated with :, or none, from hours
                        (?P=hmssep)
                        (?P<second>[0-9]{2})
                    )?
                )?

                # fractions
                (?: [,.] (?P<frac>[0-9]{1,10}))?

                # timezone, Z, +-hh or +-hh:?mm. MUST BE, but complain if not there.
                (
                    (?P<tzempty>Z)
                |
                    (?P<tzh>[+-][0-9]{2})
                    (?: :? # optional separator
                        (?P<tzm>[0-9]{2})
                    )?
                )?
            )
        )?
        $
    """, re.X) # """

    def parse_iso(timestamp):
        """Internal function for parsing a timestamp in
        ISO 8601 format"""

        timestamp = timestamp.strip()

        m = _iso8601_parser.match(timestamp)
        if not m:
            raise ValueError("Not a proper ISO 8601 timestamp!: %s" % timestamp)

        vals = m.groupdict()
        def_vals = {'year': 1970, 'month': 1, 'day': 1}
        for key in vals:
            if vals[key] is None:
                vals[key] = def_vals.get(key, 0)
            elif key not in ['time', 'ymdsep', 'hmssep', 'tzempty']:
                vals[key] = int(vals[key])

        year  = vals['year']
        month = vals['month']
        day   = vals['day']

        if m.group('time') is None:
            return datetime.date(year, month, day)

        h, min, s, us = None, None, None, 0
        frac = 0
        if m.group('tzempty') == None and m.group('tzh') == None:
            raise ValueError("Not a proper ISO 8601 timestamp: " +
                    "missing timezone (Z or +hh[:mm])!")

        if m.group('frac'):
            frac = m.group('frac')
            power = len(frac)
            frac  = int(frac) / 10.0 ** power

        if m.group('hour'):
            h = vals['hour']

        if m.group('minute'):
            min = vals['minute']

        if m.group('second'):
            s = vals['second']

        if frac != None:
            # ok, fractions of hour?
            if min == None:
                frac, min = math.modf(frac * 60.0)
                min = int(min)

            # fractions of second?
            if s == None:
                frac, s = math.modf(frac * 60.0)
                s = int(s)

            # and extract microseconds...
            us = int(frac * 1000000)

        if m.group('tzempty') == 'Z':
            offsetmins = 0
        else:
            # timezone: hour diff with sign
            offsetmins = vals['tzh'] * 60
            tzm = m.group('tzm')

            # add optional minutes
            if tzm != None:
                tzm = int(tzm)
                offsetmins += tzm if offsetmins > 0 else -tzm

        tz = _get_fixed_offset_tz(offsetmins)
        return datetime.datetime(year, month, day, h, min, s, us, tz)
