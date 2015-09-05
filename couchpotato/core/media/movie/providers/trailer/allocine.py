#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
A module to use Allocine API V3 in Python
Repository: https://github.com/xbgmsharp/allocine
Base on work from: https://github.com/gromez/allocine-api
License: LGPLv2 http://www.gnu.org/licenses/lgpl.html

Sample code:

    from allocine import allocine
    api = allocine()
    api.configure('100043982026','29d185d98c984a359e6e6f26a0474269')
    movie = api.movie(27405)
    search = api.search("Oblivion")

"""
# Debug
#from pprint import pprint
# standard module
from datetime import date
import urllib2, urllib
import hashlib, base64
import json as simplejson

__version__ = "0.2"
__author__ = "Francois Lacroix"
__license__ = "GPL"
__description__ = "A module to use Allocine API V3 in Python"

class allocine(object):
    """An interface to the Allocine API"""
    def __init__(self, partner_key=None, secret_key=None):
        """Init values"""
        self._api_url = 'http://api.allocine.fr/rest/v3'
        self._partner_key  = 'aXBob25lLXYy'
        self._secret_key = secret_key
        self._user_agent = 'AlloCine/2.9.5 CFNetwork/548.1.4 Darwin/11.0.0'

    def configure(self, partner_key=None, secret_key=None):
        """Set the keys"""
        self._partner_key = 'aXBob25lLXYy'
        self._secret_key = secret_key

    def _do_request(self, method=None, params=None):
        """Generate and send the request"""
        # build the URL
        query_url = self._api_url+'/'+method;

        # new algo to build the query
        today = date.today()
        sed = today.strftime('%Y%m%d')
        #print sed
        sha1 = hashlib.sha1(self._secret_key+urllib.urlencode(params)+'&sed='+sed).digest()
        #print sha1
        b64 = base64.b64encode(sha1)
        #print b64
        sig = urllib2.quote(b64)
        #query_url += '?'+urllib.urlencode(params)+'&sed='+sed+'&sig='+sig
        query_url += '?'+urllib.urlencode(params, True)
        #print query_url;

        # do the request
        req = urllib2.Request(query_url)
        req.add_header('User-agent', self._user_agent)

        response = simplejson.load(urllib2.urlopen(req, timeout = 10))

        return response;
    
    def search(self, query, filter="movie"):
        """Search for a term
        Param:
            query -- Term to search for
            filter -- Filter by resut type (movie, theater, person, news, tvseries)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['q'] = query
        params['filter'] = filter
        params['profile'] = "large"

        # do the request
        response = self._do_request('search', params);

        return response;

    def movie(self, id, profile="large", mediafmt="mp4-lc:m"):
        """Get the movie details by ID
        Param:
            id -- Unique ID of the movie your search for
            profile -- Level of details to return (small, medium, large)
            mediafmt -- The media format (flv, mp4-lc, mp4-hip, mp4-archive, mpeg2-theater, mpeg2)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['mediafmt'] = mediafmt
        params['profile'] = profile
        params['code'] = id
        params['striptags'] = 'synopsis,synopsisshort'

        # do the request
        response = self._do_request('movie', params);

        return response;

    def tvseries(self, id, profile="large", mediafmt="mp4-lc:m"):
        """Get the TVshow details by ID
        Param:
            id -- Unique ID of the tvseries your search for
            profile -- Level of details to return (small, medium, large)
            mediafmt -- The media format (flv, mp4-lc, mp4-hip, mp4-archive, mpeg2-theater, mpeg2)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['mediafmt'] = mediafmt
        params['profile'] = profile
        params['code'] = id
        params['striptags'] = 'synopsis,synopsisshort'

        # do the request
        response = self._do_request('tvseries', params);

        return response;

    def season(self, id, profile="large"):
        """Get the season details by ID
        Param:
            id -- Unique ID of the season your search for
            profile -- Level of details to return (small, medium, large)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['profile'] = profile
        params['code'] = id
        params['striptags'] = 'synopsis,synopsisshort'

        # do the request
        response = self._do_request('season', params);

        return response;

    def episode(self, id, profile="large"):
        """Get the episode details by ID
        Param:
            id -- Unique ID of the episode your search for
            profile -- Level of details to return (small, medium, large)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['profile'] = profile
        params['code'] = id
        params['striptags'] = 'synopsis,synopsisshort'

        # do the request
        response = self._do_request('episode', params);

        return response;
    
    def trailer(self, id, profile="large", mediafmt="mp4-lc:m"):
        """Get the movie details by ID
        Param:
            id -- Unique ID of the movie your search for
            profile -- Level of details to return (small, medium, large)
            mediafmt -- The media format (flv, mp4-lc, mp4-hip, mp4-archive, mpeg2-theater, mpeg2)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key        
        params['profile'] = profile
        params['code'] = id

        # do the request
        response = self._do_request('media',params);

        return response;
    
    def movielist(self, typemovie, profile="large", mediafmt="mp4-lc:m"):
        """Get the movie details by ID
        Param:
            id -- Unique ID of the movie your search for
            profile -- Level of details to return (small, medium, large)
            mediafmt -- The media format (flv, mp4-lc, mp4-hip, mp4-archive, mpeg2-theater, mpeg2)
        """
        # build the params
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key        
        params['profile'] = profile
        params['filter'] = typemovie
        params['order'] = 'toprank'
        params['count'] = 30

        # do the request
        response = self._do_request('movielist',params);

        return response;
