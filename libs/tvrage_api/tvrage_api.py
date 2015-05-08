# !/usr/bin/env python2
# encoding:utf-8
# author:echel0n
# project:tvrage_api
#repository:http://github.com/echel0n/tvrage_api (copied from SickRage, modified to use urllib2)
#license:unlicense (http://unlicense.org/)

"""
Modified from http://github.com/dbr/tvrage_api
Simple-to-use Python interface to The TVRage's API (tvrage.com)
"""
from functools import wraps
import traceback

__author__ = "echel0n"
__version__ = "1.0"

import os
import re
import time
import urllib
import urllib2
import getpass
import tempfile
import warnings
import logging
import datetime as dt
import xmltodict

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

from dateutil.parser import parse
from tvrage_cache import CacheHandler

from tvrage_ui import BaseUI
from tvrage_exceptions import (tvrage_error, tvrage_userabort, tvrage_shownotfound, tvrage_showincomplete,
                               tvrage_seasonnotfound, tvrage_episodenotfound, tvrage_attributenotfound)


def log():
    return logging.getLogger("tvrage_api")


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


class ShowContainer(dict):
    """Simple dict that holds a series of Show instances
    """

    def __init__(self):
        self._stack = []
        self._lastgc = time.time()

    def __setitem__(self, key, value):
        self._stack.append(key)

        #keep only the 100th latest results
        if time.time() - self._lastgc > 20:
            for o in self._stack[:-100]:
                del self[o]

            self._stack = self._stack[-100:]

            self._lastgc = time.time()

        super(ShowContainer, self).__setitem__(key, value)


class Show(dict):
    """Holds a dict of seasons, and show data.
    """

    def __init__(self):
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        return "<Show %s (containing %s seasons)>" % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getattr__(self, key):
        if key in self:
            # Key is an episode, return it
            return self[key]

        if key in self.data:
            # Non-numeric request is for show-data
            return self.data[key]

        raise AttributeError

    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)

        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if isinstance(key, int) or key.isdigit():
            # Episode number x was not found
            raise tvrage_seasonnotfound("Could not find season %s" % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise tvrage_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def airedOn(self, date):
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise tvrage_episodenotfound("Could not find any episodes that aired on %s" % date)
        return ret

    def search(self, term=None, key=None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)

        Always returns an array (can be empty). First index contains the first
        match, and so on.

        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrieve the episode name of the
        first match.

        Search terms are converted to lower case (unicode) strings.
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term=term, key=key)
            if len(searchresult) != 0:
                results.extend(searchresult)

        return results


class Season(dict):
    def __init__(self, show=None):
        """The show attribute points to the parent show
        """
        self.show = show

    def __repr__(self):
        return "<Season instance (containing %s episodes)>" % (
            len(self.keys())
        )

    def __getattr__(self, episode_number):
        if episode_number in self:
            return self[episode_number]
        raise AttributeError

    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise tvrage_episodenotfound("Could not find episode %s" % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term=None, key=None):
        """Search all episodes in season, returns a list of matching Episode
        instances.
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term=term, key=key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results


class Episode(dict):
    def __init__(self, season=None):
        """The season attribute points to the parent season
        """
        self.season = season

    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return "<Episode %02dx%02d - %s>" % (seasno, epno, epname)
        else:
            return "<Episode %02dx%02d>" % (seasno, epno)

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise tvrage_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def search(self, term=None, key=None):
        """Search episode data for term, if it matches, return the Episode (self).
        The key parameter can be used to limit the search to a specific element,
        for example, episodename.

        This primarily for use use by Show.search and Season.search.
        """
        if term == None:
            raise TypeError("must supply string to search for (contents)")

        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find(unicode(term).lower()) > -1:
                return self


class TVRage:
    """Create easy-to-use interface to name of season/episode name"""

    def __init__(self,
                 interactive=False,
                 select_first=False,
                 debug=False,
                 cache=True,
                 banners=False,
                 actors=False,
                 custom_ui=None,
                 language=None,
                 search_all_languages=False,
                 apikey=None,
                 forceConnect=False,
                 useZip=False,
                 dvdorder=False,
                 proxy=None):

        """
        cache (True/False/str/unicode/urllib2 opener):
            Retrieved XML are persisted to to disc. If true, stores in
            tvrage_api folder under your systems TEMP_DIR, if set to
            str/unicode instance it will use this as the cache
            location. If False, disables caching.  Can also be passed
            an arbitrary Python object, which is used as a urllib2
            opener, which should be created by urllib2.build_opener

        forceConnect (bool):
            If true it will always try to connect to tvrage.com even if we
            recently timed out. By default it will wait one minute before
            trying again, and any requests within that one minute window will
            return an exception immediately.
        """

        self.shows = ShowContainer()  # Holds all Show classes
        self.corrections = {}  # Holds show-name to show_id mapping

        self.config = {}

        if apikey is not None:
            self.config['apikey'] = apikey
        else:
            self.config['apikey'] = "Uhewg1Rr0o62fvZvUIZt"  # tvdb_api's API key

        self.config['debug_enabled'] = debug  # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['proxy'] = proxy

        if cache is True:
            self.config['cache_enabled'] = True
            self.config['cache_location'] = self._getTempDir()
            self.urlopener = urllib2.build_opener(
                CacheHandler(self.config['cache_location'])
            )

        elif cache is False:
            self.config['cache_enabled'] = False
            self.urlopener = urllib2.build_opener() # default opener with no caching

        elif isinstance(cache, basestring):
            self.config['cache_enabled'] = True
            self.config['cache_location'] = cache
            self.urlopener = urllib2.build_opener(
                CacheHandler(self.config['cache_location'])
            )

        elif isinstance(cache, urllib2.OpenerDirector):
            # If passed something from urllib2.build_opener, use that
            log().debug("Using %r as urlopener" % cache)
            self.config['cache_enabled'] = True
            self.urlopener = cache

        else:
            raise ValueError("Invalid value for Cache %r (type was %s)" % (cache, type(cache)))

        if self.config['debug_enabled']:
            warnings.warn("The debug argument to tvrage_api.__init__ will be removed in the next version. "
                          "To enable debug messages, use the following code before importing: "
                          "import logging; logging.basicConfig(level=logging.DEBUG)")
            logging.basicConfig(level=logging.DEBUG)


        # List of language from http://tvrage.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://tvrage.com/wiki/index.php/API:languages.xml
        self.config['valid_languages'] = [
            "da", "fi", "nl", "de", "it", "es", "fr", "pl", "hu", "el", "tr",
            "ru", "he", "ja", "pt", "zh", "cs", "sl", "hr", "ko", "en", "sv", "no"
        ]

        # tvrage.com should be based around numeric language codes,
        # but to link to a series like http://tvrage.com/?tab=series&id=79349&lid=16
        # requires the language ID, thus this mapping is required (mainly
        # for usage in tvrage_ui - internally tvrage_api will use the language abbreviations)
        self.config['langabbv_to_id'] = {'el': 20, 'en': 7, 'zh': 27,
                                         'it': 15, 'cs': 28, 'es': 16, 'ru': 22, 'nl': 13, 'pt': 26, 'no': 9,
                                         'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31, 'de': 14, 'da': 10, 'fi': 11,
                                         'hu': 19, 'ja': 25, 'he': 24, 'ko': 32, 'sv': 8, 'sl': 30}

        if language is None:
            self.config['language'] = 'en'
        else:
            if language not in self.config['valid_languages']:
                raise ValueError("Invalid language %s, options are: %s" % (
                    language, self.config['valid_languages']
                ))
            else:
                self.config['language'] = language

        # The following url_ configs are based of the
        # http://tvrage.com/wiki/index.php/Programmers_API

        self.config['base_url'] = "http://services.tvrage.com"

        self.config['url_getSeries'] = u"%(base_url)s/feeds/search.php?show=%%s" % self.config

        self.config['url_epInfo'] = u"%(base_url)s/myfeeds/episode_list.php?key=%(apikey)s&sid=%%s" % self.config

        self.config['url_seriesInfo'] = u"%(base_url)s/myfeeds/showinfo.php?key=%(apikey)s&sid=%%s" % self.config

        self.config['url_updtes_all'] = u"%(base_url)s/myfeeds/currentshows.php" % self.config

    def _getTempDir(self):
        """Returns the [system temp dir]/tvrage_api-u501 (or
        tvrage_api-myuser)
        """
        if hasattr(os, 'getuid'):
            uid = "u%d" % (os.getuid())
        else:
            # For Windows
            try:
                uid = getpass.getuser()
            except ImportError:
                return os.path.join(tempfile.gettempdir(), "tvrage_api")

        return os.path.join(tempfile.gettempdir(), "tvrage_api-%s" % (uid))

    @retry(tvrage_error)
    def _loadUrl(self, url):
        global lastTimeout
        try:
            log().debug("Retrieving URL %s" % url)
            resp = self.urlopener.open(url)
            if 'x-local-cache' in resp.headers:
                log().debug("URL %s was cached in %s" % (
                    url,
                    resp.headers['x-local-cache'])
                )
        except (IOError, urllib2.URLError), errormsg:
            if not str(errormsg).startswith('HTTP Error'):
                lastTimeout = datetime.datetime.now()
            raise tvrage_error("Could not connect to server: %s" % (errormsg))


        # handle gzipped content,
        # http://dbr.lighthouseapp.com/projects/13342/tickets/72-gzipped-data-patch
        if 'gzip' in resp.headers.get("Content-Encoding", ''):
            if gzip:
                stream = StringIO.StringIO(resp.read())
                gz = gzip.GzipFile(fileobj=stream)
                return gz.read()

            raise tvrage_error("Received gzip data from thetvdb.com, but could not correctly handle it")

        def remap_keys(path, key, value):
            name_map = {
                'showid': 'id',
                'showname': 'seriesname',
                'name': 'seriesname',
                'summary': 'overview',
                'started': 'firstaired',
                'genres': 'genre',
                'airtime': 'airs_time',
                'airday': 'airs_dayofweek',
                'image': 'fanart',
                'epnum': 'absolute_number',
                'title': 'episodename',
                'airdate': 'firstaired',
                'screencap': 'filename',
                'seasonnum': 'episodenumber'
            }

            status_map = {
                'returning series': 'Continuing',
                'canceled/ended': 'Ended',
                'tbd/on the bubble': 'Continuing',
                'in development': 'Continuing',
                'new series': 'Continuing',
                'never aired': 'Ended',
                'final season': 'Continuing',
                'on hiatus': 'Continuing',
                'pilot ordered': 'Continuing',
                'pilot rejected': 'Ended',
                'canceled': 'Ended',
                'ended': 'Ended',
                '': 'Unknown',
            }

            try:
                key = name_map[key.lower()]
            except (ValueError, TypeError, KeyError):
                key = key.lower()

            # clean up value and do type changes
            if value:
                if isinstance(value, dict):
                    if key == 'status':
                        try:
                            value = status_map[str(value).lower()]
                            if not value:
                                raise
                        except:
                            value = 'Unknown'

                    if key == 'network':
                        value = value['#text']

                    if key == 'genre':
                        value = value['genre']
                        if not value:
                            value = []
                        if not isinstance(value, list):
                            value = [value]
                        value = filter(None, value)
                        value = '|' + '|'.join(value) + '|'

                try:
                    if key == 'firstaired' and value in "0000-00-00":
                        new_value = str(dt.date.fromordinal(1))
                        new_value = re.sub("([-]0{2}){1,}", "", new_value)
                        fixDate = parse(new_value, fuzzy=True).date()
                        value = fixDate.strftime("%Y-%m-%d")
                    elif key == 'firstaired':
                        value = parse(value, fuzzy=True).date()
                        value = value.strftime("%Y-%m-%d")
                except:
                    pass

            return (key, value)

        try:
            return xmltodict.parse(resp.read(), postprocessor=remap_keys)
        except:
            return dict([(u'data', None)])

    def _getetsrc(self, url):
        """Loads a URL using caching, returns an ElementTree of the source
        """

        try:
            return self._loadUrl(url).values()[0]
        except Exception, e:
            raise tvrage_error(e)

    def _setItem(self, sid, seas, ep, attrib, value):
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getShowData to populate show

        Since the nice-to-use tvrage[1][24]['name] interface
        makes it impossible to do tvrage[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvrage_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvrage[1][24]['episodename'] = "name"
        calls __getitem__ on tvrage[1], there is no way to check if
        tvrage.__dict__ should have a key "1" before we auto-create it
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        if seas not in self.shows[sid]:
            self.shows[sid][seas] = Season(show=self.shows[sid])
        if ep not in self.shows[sid][seas]:
            self.shows[sid][seas][ep] = Episode(season=self.shows[sid][seas])
        self.shows[sid][seas][ep][attrib] = value

    def _setShowData(self, sid, key, value):
        """Sets self.shows[sid] to a new Show instance, or sets the data
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def _cleanData(self, data):
        """Cleans up strings returned by tvrage.com

        Issues corrected:
        - Replaces &amp; with &
        - Trailing whitespace
        """

        if isinstance(data, basestring):
            data = data.replace(u"&amp;", u"&")
            data = data.strip()

        return data

    def search(self, series):
        """This searches tvrage.com for the series name
        and returns the result list
        """
        series = series.encode("utf-8")
        log().debug("Searching for show %s" % series)

        return self._getetsrc(self.config['url_getSeries'] % (series)).values()[0]

    def _getSeries(self, series):
        """This searches tvrage.com for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.
        """
        allSeries = self.search(series)
        if not allSeries:
            log().debug('Series result returned zero')
            raise tvrage_shownotfound("Show search returned zero results (cannot find show on TVRAGE)")

        if not isinstance(allSeries, list):
            allSeries = [allSeries]

        if self.config['custom_ui'] is not None:
            log().debug("Using custom UI %s" % (repr(self.config['custom_ui'])))
            CustomUI = self.config['custom_ui']
            ui = CustomUI(config=self.config)
        else:
            log().debug('Auto-selecting first search result using BaseUI')
            ui = BaseUI(config=self.config)

        return ui.selectSeries(allSeries)

    def _getShowData(self, sid, getEpInfo=False):
        """Takes a series ID, gets the epInfo URL and parses the TVRAGE
        XML file into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """

        # Parse show information
        log().debug('Getting all series data for %s' % (sid))
        seriesInfoEt = self._getetsrc(self.config['url_seriesInfo'] % (sid))

        if not seriesInfoEt:
            log().debug('Series result returned zero')
            raise tvrage_error("Series result returned zero")

        # get series data
        for k, v in seriesInfoEt.items():
            if v is not None:
                v = self._cleanData(v)

            self._setShowData(sid, k, v)

        # get episode data
        if getEpInfo:
            # Parse episode data
            log().debug('Getting all episodes of %s' % (sid))
            epsEt = self._getetsrc(self.config['url_epInfo'] % (sid))

            if not epsEt:
                log().debug('Series results incomplete')
                raise tvrage_showincomplete(
                    "Show search returned incomplete results (cannot find complete show on TVRAGE)")

            if 'episodelist' not in epsEt:
                return False

            seasons = epsEt['episodelist']['season']
            if not isinstance(seasons, list):
                seasons = [seasons]

            for season in seasons:
                seas_no = int(season['@no'])

                episodes = season['episode']
                if not isinstance(episodes, list):
                    episodes = [episodes]

                for episode in episodes:
                    ep_no = int(episode['episodenumber'])

                    for k, v in episode.items():
                        k = k.lower()

                        if v is not None:
                            if k == 'link':
                                v = v.rsplit('/', 1)[1]
                                k = 'id'
                            else:
                                v = self._cleanData(v)

                        self._setItem(sid, seas_no, ep_no, k, v)

        return True

    def _nameToSid(self, name):
        """Takes show name, returns the correct series ID (if the show has
        already been grabbed), or grabs all episodes and returns
        the correct SID.
        """
        if name in self.corrections:
            log().debug('Correcting %s to %s' % (name, self.corrections[name]))
            return self.corrections[name]
        else:
            log().debug('Getting show %s' % (name))
            selected_series = self._getSeries(name)
            if isinstance(selected_series, dict):
                selected_series = [selected_series]
            sids = list(int(x['id']) for x in selected_series if self._getShowData(int(x['id'])))
            self.corrections.update(dict((x['seriesname'], int(x['id'])) for x in selected_series))
            return sids

    def __getitem__(self, key):
        """Handles tvrage_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._getShowData(key, True)
            return self.shows[key]

        key = str(key).lower()
        self.config['searchterm'] = key
        selected_series = self._getSeries(key)
        if isinstance(selected_series, dict):
            selected_series = [selected_series]
        [[self._setShowData(show['id'], k, v) for k, v in show.items()] for show in selected_series]
        return selected_series
        #test = self._getSeries(key)
        #sids = self._nameToSid(key)
        #return list(self.shows[sid] for sid in sids)

    def __repr__(self):
        return str(self.shows)


def main():
    """Simple example of using tvrage_api - it just
    grabs an episode name interactively.
    """
    import logging

    logging.basicConfig(level=logging.DEBUG)

    tvrage_instance = TVRage(cache=False)
    print tvrage_instance['Lost']['seriesname']
    print tvrage_instance['Lost'][1][4]['episodename']


if __name__ == '__main__':
    main()
