#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: tmdb_auth.py
# Python Library
# Author: Raymond Wagner
# Purpose: Provide authentication and session services for 
#          calls against the TMDB v3 API
#-----------------------

from datetime import datetime as _pydatetime, \
                     tzinfo as _pytzinfo
import re
class datetime(_pydatetime):
    """Customized datetime class with ISO format parsing."""
    _reiso = re.compile('(?P<year>[0-9]{4})'
                       '-(?P<month>[0-9]{1,2})'
                       '-(?P<day>[0-9]{1,2})'
                        '.'
                        '(?P<hour>[0-9]{2})'
                       ':(?P<min>[0-9]{2})'
                       '(:(?P<sec>[0-9]{2}))?'
                        '(?P<tz>Z|'
                            '(?P<tzdirec>[-+])'
                            '(?P<tzhour>[0-9]{1,2})'
                            '(:)?'
                            '(?P<tzmin>[0-9]{2})?'
                        ')?')

    class _tzinfo(_pytzinfo):
        def __init__(self, direc='+', hr=0, min=0):
            if direc == '-':
                hr = -1*int(hr)
            self._offset = timedelta(hours=int(hr), minutes=int(min))

        def utcoffset(self, dt):
            return self._offset

        def tzname(self, dt):
            return ''

        def dst(self, dt):
            return timedelta(0)

    @classmethod
    def fromIso(cls, isotime, sep='T'):
        match = cls._reiso.match(isotime)
        if match is None:
            raise TypeError("time data '%s' does not match ISO 8601 format"
                            % isotime)

        dt = [int(a) for a in match.groups()[:5]]
        if match.group('sec') is not None:
            dt.append(int(match.group('sec')))
        else:
            dt.append(0)
        if match.group('tz'):
            if match.group('tz') == 'Z':
                tz = cls._tzinfo()
            elif match.group('tzmin'):
                tz = cls._tzinfo(*match.group('tzdirec', 'tzhour', 'tzmin'))
            else:
                tz = cls._tzinfo(*match.group('tzdirec', 'tzhour'))
            dt.append(0)
            dt.append(tz)
        return cls(*dt)

from request import Request
from tmdb_exceptions import *

syssession = None


def set_session(sessionid):
    global syssession
    syssession = Session(sessionid)


def get_session(sessionid=None):
    global syssession
    if sessionid:
        return Session(sessionid)
    elif syssession is not None:
        return syssession
    else:
        return Session.new()


class Session(object):
    @classmethod
    def new(cls):
        return cls(None)

    def __init__(self, sessionid):
        self.sessionid = sessionid

    @property
    def sessionid(self):
        if self._sessionid is None:
            if self._authtoken is None:
                raise TMDBError("No Auth Token to produce Session for")
            # TODO: check authtoken expiration against current time
            req = Request('authentication/session/new',
                          request_token=self._authtoken)
            req.lifetime = 0
            dat = req.readJSON()
            if not dat['success']:
                raise TMDBError("Session generation failed")
            self._sessionid = dat['session_id']
        return self._sessionid

    @sessionid.setter
    def sessionid(self, value):
        self._sessionid = value
        self._authtoken = None
        self._authtokenexpiration = None
        if value is None:
            self.authenticated = False
        else:
            self.authenticated = True

    @property
    def authtoken(self):
        if self.authenticated:
            raise TMDBError("Session is already authenticated")
        if self._authtoken is None:
            req = Request('authentication/token/new')
            req.lifetime = 0
            dat = req.readJSON()
            if not dat['success']:
                raise TMDBError("Auth Token request failed")
            self._authtoken = dat['request_token']
            self._authtokenexpiration = datetime.fromIso(dat['expires_at'])
        return self._authtoken

    @property
    def callbackurl(self):
        return "http://www.themoviedb.org/authenticate/"+self._authtoken
