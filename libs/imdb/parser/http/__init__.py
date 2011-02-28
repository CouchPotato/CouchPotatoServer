"""
parser.http package (imdb package).

This package provides the IMDbHTTPAccessSystem class used to access
IMDb's data through the web interface.
the imdb.IMDb function will return an instance of this class when
called with the 'accessSystem' argument set to "http" or "web"
or "html" (this is the default).

Copyright 2004-2010 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import sys
import logging
from urllib import FancyURLopener, quote_plus
from codecs import lookup

from imdb import IMDbBase, imdbURL_movie_main, imdbURL_person_main, \
                imdbURL_character_main, imdbURL_company_main, \
                imdbURL_keyword_main, imdbURL_find, imdbURL_top250, \
                imdbURL_bottom100
from imdb.utils import analyze_title
from imdb._exceptions import IMDbDataAccessError, IMDbParserError

import searchMovieParser
import searchPersonParser
import searchCharacterParser
import searchCompanyParser
import searchKeywordParser
import movieParser
import personParser
import characterParser
import companyParser
import topBottomParser

# Logger for miscellaneous functions.
_aux_logger = logging.getLogger('imdbpy.parser.http.aux')

IN_GAE = False
try:
    import google.appengine
    IN_GAE = True
    _aux_logger.info('IMDbPY is running in the Google App Engine environment')
except ImportError:
    pass


class _ModuleProxy:
    """A proxy to instantiate and access parsers."""
    def __init__(self, module, defaultKeys=None, oldParsers=False,
                useModule=None, fallBackToNew=False):
        """Initialize a proxy for the given module; defaultKeys, if set,
        muste be a dictionary of values to set for instanced objects."""
        if oldParsers or fallBackToNew:
            _aux_logger.warn('The old set of parsers was removed; falling ' \
                            'back to the new parsers.')
        self.useModule = useModule
        if defaultKeys is None:
            defaultKeys = {}
        self._defaultKeys = defaultKeys
        self._module = module

    def __getattr__(self, name):
        """Called only when no look-up is found."""
        _sm = self._module
        # Read the _OBJECTS dictionary to build the asked parser.
        if name in _sm._OBJECTS:
            _entry = _sm._OBJECTS[name]
            # Initialize the parser.
            kwds = {}
            if self.useModule:
                kwds = {'useModule': self.useModule}
            parserClass = _entry[0][0]
            obj = parserClass(**kwds)
            attrsToSet = self._defaultKeys.copy()
            attrsToSet.update(_entry[1] or {})
            # Set attribute to the object.
            for key in attrsToSet:
                setattr(obj, key, attrsToSet[key])
            setattr(self, name, obj)
            return obj
        return getattr(_sm, name)


PY_VERSION = sys.version_info[:2]


# The cookies for the "adult" search.
# Please don't mess with these account.
# Old 'IMDbPY' account.
_old_cookie_id = 'boM2bYxz9MCsOnH9gZ0S9QHs12NWrNdApxsls1Vb5/NGrNdjcHx3dUas10UASoAjVEvhAbGagERgOpNkAPvxdbfKwaV2ikEj9SzXY1WPxABmDKQwdqzwRbM+12NSeJFGUEx3F8as10WwidLzVshDtxaPIbP13NdjVS9UZTYqgTVGrNcT9vyXU1'
_old_cookie_uu = '3M3AXsquTU5Gur/Svik+ewflPm5Rk2ieY3BIPlLjyK3C0Dp9F8UoPgbTyKiGtZp4x1X+uAUGKD7BM2g+dVd8eqEzDErCoYvdcvGLvVLAen1y08hNQtALjVKAe+1hM8g9QbNonlG1/t4S82ieUsBbrSIQbq1yhV6tZ6ArvSbA7rgHc8n5AdReyAmDaJ5Wm/ee3VDoCnGj/LlBs2ieUZNorhHDKK5Q=='
# New 'IMDbPYweb' account.
_cookie_id = 'rH1jNAkjTlNXvHolvBVBsgaPICNZbNdjVjzFwzas9JRmusdjVoqBs/Hs12NR+1WFxEoR9bGKEDUg6sNlADqXwkas12N131Rwdb+UQNGKN8PWrNdjcdqBQVLq8mbGDHP3hqzxhbD692NQi9D0JjpBtRaPIbP1zNdjUOqENQYv1ADWrNcT9vyXU1'
_cookie_uu = 'su4/m8cho4c6HP+W1qgq6wchOmhnF0w+lIWvHjRUPJ6nRA9sccEafjGADJ6hQGrMd4GKqLcz2X4z5+w+M4OIKnRn7FpENH7dxDQu3bQEHyx0ZEyeRFTPHfQEX03XF+yeN1dsPpcXaqjUZAw+lGRfXRQEfz3RIX9IgVEffdBAHw2wQXyf9xdMPrQELw0QNB8dsffsqcdQemjPB0w+moLcPh0JrKrHJ9hjBzdMPpcXTH7XRwwOk='


class _FakeURLOpener(object):
    """Fake URLOpener object, used to return empty strings instead of
    errors.
    """
    def __init__(self, url, headers):
        self.url = url
        self.headers = headers
    def read(self, *args, **kwds): return ''
    def close(self, *args, **kwds): pass
    def info(self, *args, **kwds): return self.headers


class IMDbURLopener(FancyURLopener):
    """Fetch web pages and handle errors."""
    _logger = logging.getLogger('imdbpy.parser.http.urlopener')

    def __init__(self, *args, **kwargs):
        self._last_url = u''
        FancyURLopener.__init__(self, *args, **kwargs)
        # Headers to add to every request.
        # XXX: IMDb's web server doesn't like urllib-based programs,
        #      so lets fake to be Mozilla.
        #      Wow!  I'm shocked by my total lack of ethic! <g>
        for header in ('User-Agent', 'User-agent', 'user-agent'):
            self.del_header(header)
        self.set_header('User-Agent', 'Mozilla/5.0')
        # XXX: This class is used also to perform "Exact Primary
        #      [Title|Name]" searches, and so by default the cookie is set.
        c_header = 'id=%s; uu=%s' % (_cookie_id, _cookie_uu)
        self.set_header('Cookie', c_header)

    def get_proxy(self):
        """Return the used proxy, or an empty string."""
        return self.proxies.get('http', '')

    def set_proxy(self, proxy):
        """Set the proxy."""
        if not proxy:
            if self.proxies.has_key('http'):
                del self.proxies['http']
        else:
            if not proxy.lower().startswith('http://'):
                proxy = 'http://%s' % proxy
            self.proxies['http'] = proxy

    def set_header(self, header, value, _overwrite=True):
        """Set a default header."""
        if _overwrite:
            self.del_header(header)
        self.addheaders.append((header, value))

    def del_header(self, header):
        """Remove a default header."""
        for index in xrange(len(self.addheaders)):
            if self.addheaders[index][0] == header:
                del self.addheaders[index]
                break

    def retrieve_unicode(self, url, size=-1):
        """Retrieves the given URL, and returns a unicode string,
        trying to guess the encoding of the data (assuming latin_1
        by default)"""
        encode = None
        try:
            if size != -1:
                self.set_header('Range', 'bytes=0-%d' % size)
            uopener = self.open(url)
            kwds = {}
            if PY_VERSION > (2, 3) and not IN_GAE:
                kwds['size'] = size
            content = uopener.read(**kwds)
            self._last_url = uopener.url
            # Maybe the server is so nice to tell us the charset...
            server_encode = uopener.info().getparam('charset')
            # Otherwise, look at the content-type HTML meta tag.
            if server_encode is None and content:
                first_bytes = content[:512]
                begin_h = first_bytes.find('text/html; charset=')
                if begin_h != -1:
                    end_h = first_bytes[19+begin_h:].find('"')
                    if end_h != -1:
                        server_encode = first_bytes[19+begin_h:19+begin_h+end_h]
            if server_encode:
                try:
                    if lookup(server_encode):
                        encode = server_encode
                except (LookupError, ValueError, TypeError):
                    pass
            uopener.close()
            if size != -1:
                self.del_header('Range')
            self.close()
        except IOError, e:
            if size != -1:
                # Ensure that the Range header is removed.
                self.del_header('Range')
            raise IMDbDataAccessError, {'errcode': e.errno,
                                        'errmsg': str(e.strerror),
                                        'url': url,
                                        'proxy': self.get_proxy(),
                                        'exception type': 'IOError',
                                        'original exception': e}
        if encode is None:
            encode = 'latin_1'
            # The detection of the encoding is error prone...
            self._logger.warn('Unable to detect the encoding of the retrieved '
                        'page [%s]; falling back to default latin1.', encode)
        ##print unicode(content, encode, 'replace').encode('utf8')
        return unicode(content, encode, 'replace')

    def http_error_default(self, url, fp, errcode, errmsg, headers):
        if errcode == 404:
            self._logger.warn('404 code returned for %s: %s (headers: %s)',
                                url, errmsg, headers)
            return _FakeURLOpener(url, headers)
        raise IMDbDataAccessError, {'url': 'http:%s' % url,
                                    'errcode': errcode,
                                    'errmsg': errmsg,
                                    'headers': headers,
                                    'error type': 'http_error_default',
                                    'proxy': self.get_proxy()}

    def open_unknown(self, fullurl, data=None):
        raise IMDbDataAccessError, {'fullurl': fullurl,
                                    'data': str(data),
                                    'error type': 'open_unknown',
                                    'proxy': self.get_proxy()}

    def open_unknown_proxy(self, proxy, fullurl, data=None):
        raise IMDbDataAccessError, {'proxy': str(proxy),
                                    'fullurl': fullurl,
                                    'error type': 'open_unknown_proxy',
                                    'data': str(data)}


class IMDbHTTPAccessSystem(IMDbBase):
    """The class used to access IMDb's data through the web."""

    accessSystem = 'http'
    _http_logger = logging.getLogger('imdbpy.parser.http')

    def __init__(self, isThin=0, adultSearch=1, proxy=-1, oldParsers=False,
                fallBackToNew=False, useModule=None, cookie_id=-1,
                cookie_uu=None, *arguments, **keywords):
        """Initialize the access system."""
        IMDbBase.__init__(self, *arguments, **keywords)
        self.urlOpener =  IMDbURLopener()
        # When isThin is set, we're parsing the "maindetails" page
        # of a movie (instead of the "combined" page) and movie/person
        # references are not collected if no defaultModFunct is provided.
        self.isThin = isThin
        self._getRefs = True
        self._mdparse = False
        if isThin:
            if self.accessSystem == 'http':
                self.accessSystem = 'httpThin'
            self._mdparse = True
            if self._defModFunct is None:
                self._getRefs = False
                from imdb.utils import modNull
                self._defModFunct = modNull
        self.do_adult_search(adultSearch)
        if cookie_id != -1:
            if cookie_id is None:
                self.del_cookies()
            elif cookie_uu is not None:
                self.set_cookies(cookie_id, cookie_uu)
        if proxy != -1:
            self.set_proxy(proxy)
        if useModule is not None:
            if not isinstance(useModule, (list, tuple)) and ',' in useModule:
                useModule = useModule.split(',')
        _def = {'_modFunct': self._defModFunct, '_as': self.accessSystem}
        # Proxy objects.
        self.smProxy = _ModuleProxy(searchMovieParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.spProxy = _ModuleProxy(searchPersonParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.scProxy = _ModuleProxy(searchCharacterParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.scompProxy = _ModuleProxy(searchCompanyParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.skProxy = _ModuleProxy(searchKeywordParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.mProxy = _ModuleProxy(movieParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.pProxy = _ModuleProxy(personParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.cProxy = _ModuleProxy(characterParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.compProxy = _ModuleProxy(companyParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)
        self.topBottomProxy = _ModuleProxy(topBottomParser, defaultKeys=_def,
                                    oldParsers=oldParsers, useModule=useModule,
                                    fallBackToNew=fallBackToNew)

    def _normalize_movieID(self, movieID):
        """Normalize the given movieID."""
        try:
            return '%07d' % int(movieID)
        except ValueError, e:
            raise IMDbParserError, 'invalid movieID "%s": %s' % (movieID, e)

    def _normalize_personID(self, personID):
        """Normalize the given personID."""
        try:
            return '%07d' % int(personID)
        except ValueError, e:
            raise IMDbParserError, 'invalid personID "%s": %s' % (personID, e)

    def _normalize_characterID(self, characterID):
        """Normalize the given characterID."""
        try:
            return '%07d' % int(characterID)
        except ValueError, e:
            raise IMDbParserError, 'invalid characterID "%s": %s' % \
                    (characterID, e)

    def _normalize_companyID(self, companyID):
        """Normalize the given companyID."""
        try:
            return '%07d' % int(companyID)
        except ValueError, e:
            raise IMDbParserError, 'invalid companyID "%s": %s' % \
                    (companyID, e)

    def get_imdbMovieID(self, movieID):
        """Translate a movieID in an imdbID; in this implementation
        the movieID _is_ the imdbID.
        """
        return movieID

    def get_imdbPersonID(self, personID):
        """Translate a personID in an imdbID; in this implementation
        the personID _is_ the imdbID.
        """
        return personID

    def get_imdbCharacterID(self, characterID):
        """Translate a characterID in an imdbID; in this implementation
        the characterID _is_ the imdbID.
        """
        return characterID

    def get_imdbCompanyID(self, companyID):
        """Translate a companyID in an imdbID; in this implementation
        the companyID _is_ the imdbID.
        """
        return companyID

    def get_proxy(self):
        """Return the used proxy or an empty string."""
        return self.urlOpener.get_proxy()

    def set_proxy(self, proxy):
        """Set the web proxy to use.

        It should be a string like 'http://localhost:8080/'; if the
        string is empty, no proxy will be used.
        If set, the value of the environment variable HTTP_PROXY is
        automatically used.
        """
        self.urlOpener.set_proxy(proxy)

    def set_cookies(self, cookie_id, cookie_uu):
        """Set a cookie to access an IMDb's account."""
        c_header = 'id=%s; uu=%s' % (cookie_id, cookie_uu)
        self.urlOpener.set_header('Cookie', c_header)

    def del_cookies(self):
        """Remove the used cookie."""
        self.urlOpener.del_header('Cookie')

    def do_adult_search(self, doAdult,
                        cookie_id=_cookie_id, cookie_uu=_cookie_uu):
        """If doAdult is true, 'adult' movies are included in the
        search results; cookie_id and cookie_uu are optional
        parameters to select a specific account (see your cookie
        or cookies.txt file."""
        if doAdult:
            self.set_cookies(cookie_id, cookie_uu)
            #c_header = 'id=%s; uu=%s' % (cookie_id, cookie_uu)
            #self.urlOpener.set_header('Cookie', c_header)
        else:
            self.urlOpener.del_header('Cookie')

    def _retrieve(self, url, size=-1):
        """Retrieve the given URL."""
        ##print url
        self._http_logger.debug('fetching url %s (size: %d)', url, size)
        return self.urlOpener.retrieve_unicode(url, size=size)

    def _get_search_content(self, kind, ton, results):
        """Retrieve the web page for a given search.
        kind can be 'tt' (for titles), 'nm' (for names),
        'char' (for characters) or 'co' (for companies).
        ton is the title or the name to search.
        results is the maximum number of results to be retrieved."""
        if isinstance(ton, unicode):
            ton = ton.encode('utf-8')
        ##params = 'q=%s&%s=on&mx=%s' % (quote_plus(ton), kind, str(results))
        params = 's=%s;mx=%s;q=%s' % (kind, str(results), quote_plus(ton))
        if kind == 'ep':
            params = params.replace('s=ep;', 's=tt;ttype=ep;', 1)
        cont = self._retrieve(imdbURL_find % params)
        #print 'URL:', imdbURL_find % params
        if cont.find('Your search returned more than') == -1 or \
                cont.find("displayed the exact matches") == -1:
            return cont
        # The retrieved page contains no results, because too many
        # titles or names contain the string we're looking for.
        params = 's=%s;q=%s;lm=0' % (kind, quote_plus(ton))
        size = 22528 + results * 512
        return self._retrieve(imdbURL_find % params, size=size)

    def _search_movie(self, title, results):
        # The URL of the query.
        # XXX: To retrieve the complete results list:
        #      params = urllib.urlencode({'more': 'tt', 'q': title})
        ##params = urllib.urlencode({'tt': 'on','mx': str(results),'q': title})
        ##params = 'q=%s&tt=on&mx=%s' % (quote_plus(title), str(results))
        ##cont = self._retrieve(imdbURL_find % params)
        cont = self._get_search_content('tt', title, results)
        return self.smProxy.search_movie_parser.parse(cont, results=results)['data']

    def _search_episode(self, title, results):
        t_dict = analyze_title(title)
        if t_dict['kind'] == 'episode':
            title = t_dict['title']
        cont = self._get_search_content('ep', title, results)
        return self.smProxy.search_movie_parser.parse(cont, results=results)['data']

    def get_movie_main(self, movieID):
        if not self.isThin:
            cont = self._retrieve(imdbURL_movie_main % movieID + 'combined')
        else:
            cont = self._retrieve(imdbURL_movie_main % movieID + 'maindetails')
        return self.mProxy.movie_parser.parse(cont, mdparse=self._mdparse)

    def get_movie_full_credits(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'fullcredits')
        return self.mProxy.movie_parser.parse(cont)

    def get_movie_plot(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'plotsummary')
        return self.mProxy.plot_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_awards(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'awards')
        return self.mProxy.movie_awards_parser.parse(cont)

    def get_movie_taglines(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'taglines')
        return self.mProxy.taglines_parser.parse(cont)

    def get_movie_keywords(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'keywords')
        return self.mProxy.keywords_parser.parse(cont)

    def get_movie_alternate_versions(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'alternateversions')
        return self.mProxy.alternateversions_parser.parse(cont,
                                                        getRefs=self._getRefs)

    def get_movie_crazy_credits(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'crazycredits')
        return self.mProxy.crazycredits_parser.parse(cont,
                                                    getRefs=self._getRefs)

    def get_movie_goofs(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'goofs')
        return self.mProxy.goofs_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_quotes(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'quotes')
        return self.mProxy.quotes_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_release_dates(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'releaseinfo')
        ret = self.mProxy.releasedates_parser.parse(cont)
        ret['info sets'] = ('release dates', 'akas')
        return ret
    get_movie_akas = get_movie_release_dates

    def get_movie_vote_details(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'ratings')
        return self.mProxy.ratings_parser.parse(cont)

    def get_movie_official_sites(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'officialsites')
        return self.mProxy.officialsites_parser.parse(cont)

    def get_movie_trivia(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'trivia')
        return self.mProxy.trivia_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_connections(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'movieconnections')
        return self.mProxy.connections_parser.parse(cont)

    def get_movie_technical(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'technical')
        return self.mProxy.tech_parser.parse(cont)

    def get_movie_business(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'business')
        return self.mProxy.business_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_literature(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'literature')
        return self.mProxy.literature_parser.parse(cont)

    def get_movie_locations(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'locations')
        return self.mProxy.locations_parser.parse(cont)

    def get_movie_soundtrack(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'soundtrack')
        return self.mProxy.soundtrack_parser.parse(cont)

    def get_movie_dvd(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'dvd')
        return self.mProxy.dvd_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_recommendations(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'recommendations')
        return self.mProxy.rec_parser.parse(cont)

    def get_movie_external_reviews(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'externalreviews')
        return self.mProxy.externalrev_parser.parse(cont)

    def get_movie_newsgroup_reviews(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'newsgroupreviews')
        return self.mProxy.newsgrouprev_parser.parse(cont)

    def get_movie_misc_sites(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'miscsites')
        return self.mProxy.misclinks_parser.parse(cont)

    def get_movie_sound_clips(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'soundsites')
        return self.mProxy.soundclips_parser.parse(cont)

    def get_movie_video_clips(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'videosites')
        return self.mProxy.videoclips_parser.parse(cont)

    def get_movie_photo_sites(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'photosites')
        return self.mProxy.photosites_parser.parse(cont)

    def get_movie_news(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'news')
        return self.mProxy.news_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_amazon_reviews(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'amazon')
        return self.mProxy.amazonrev_parser.parse(cont)

    def get_movie_guests(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'epcast')
        return self.mProxy.episodes_cast_parser.parse(cont)
    get_movie_episodes_cast = get_movie_guests

    def get_movie_merchandising_links(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'sales')
        return self.mProxy.sales_parser.parse(cont)

    def get_movie_episodes(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'episodes')
        data_d = self.mProxy.episodes_parser.parse(cont)
        # set movie['episode of'].movieID for every episode of the series.
        if data_d.get('data', {}).has_key('episodes'):
            nr_eps = 0
            for season in data_d['data']['episodes'].values():
                for episode in season.values():
                    episode['episode of'].movieID = movieID
                    nr_eps += 1
            # Number of episodes.
            if nr_eps:
                data_d['data']['number of episodes'] = nr_eps
        return data_d

    def get_movie_episodes_rating(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'epdate')
        data_d = self.mProxy.eprating_parser.parse(cont)
        # set movie['episode of'].movieID for every episode.
        if data_d.get('data', {}).has_key('episodes rating'):
            for item in data_d['data']['episodes rating']:
                episode = item['episode']
                episode['episode of'].movieID = movieID
        return data_d

    def get_movie_faqs(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'faq')
        return self.mProxy.movie_faqs_parser.parse(cont, getRefs=self._getRefs)

    def get_movie_airing(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'tvschedule')
        return self.mProxy.airing_parser.parse(cont)

    get_movie_tv_schedule = get_movie_airing

    def get_movie_synopsis(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'synopsis')
        return self.mProxy.synopsis_parser.parse(cont)

    def get_movie_parents_guide(self, movieID):
        cont = self._retrieve(imdbURL_movie_main % movieID + 'parentalguide')
        return self.mProxy.parentsguide_parser.parse(cont)

    def _search_person(self, name, results):
        # The URL of the query.
        # XXX: To retrieve the complete results list:
        #      params = urllib.urlencode({'more': 'nm', 'q': name})
        ##params = urllib.urlencode({'nm': 'on', 'mx': str(results), 'q': name})
        #params = 'q=%s&nm=on&mx=%s' % (quote_plus(name), str(results))
        #cont = self._retrieve(imdbURL_find % params)
        cont = self._get_search_content('nm', name, results)
        return self.spProxy.search_person_parser.parse(cont, results=results)['data']

    def get_person_main(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'maindetails')
        ret = self.pProxy.maindetails_parser.parse(cont)
        ret['info sets'] = ('main', 'filmography')
        return ret

    def get_person_filmography(self, personID):
        return self.get_person_main(personID)

    def get_person_biography(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'bio')
        return self.pProxy.bio_parser.parse(cont, getRefs=self._getRefs)

    def get_person_awards(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'awards')
        return self.pProxy.person_awards_parser.parse(cont)

    def get_person_other_works(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'otherworks')
        return self.pProxy.otherworks_parser.parse(cont, getRefs=self._getRefs)

    #def get_person_agent(self, personID):
    #    cont = self._retrieve(imdbURL_person_main % personID + 'agent')
    #    return self.pProxy.agent_parser.parse(cont)

    def get_person_publicity(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'publicity')
        return self.pProxy.publicity_parser.parse(cont)

    def get_person_official_sites(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'officialsites')
        return self.pProxy.person_officialsites_parser.parse(cont)

    def get_person_news(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'news')
        return self.pProxy.news_parser.parse(cont)

    def get_person_episodes(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'filmoseries')
        return self.pProxy.person_series_parser.parse(cont)

    def get_person_merchandising_links(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'forsale')
        return self.pProxy.sales_parser.parse(cont)

    def get_person_genres_links(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'filmogenre')
        return self.pProxy.person_genres_parser.parse(cont)

    def get_person_keywords_links(self, personID):
        cont = self._retrieve(imdbURL_person_main % personID + 'filmokey')
        return self.pProxy.person_keywords_parser.parse(cont)

    def _search_character(self, name, results):
        cont = self._get_search_content('char', name, results)
        return self.scProxy.search_character_parser.parse(cont, results=results)['data']

    def get_character_main(self, characterID):
        cont = self._retrieve(imdbURL_character_main % characterID)
        ret = self.cProxy.character_main_parser.parse(cont)
        ret['info sets'] = ('main', 'filmography')
        return ret

    get_character_filmography = get_character_main

    def get_character_biography(self, characterID):
        cont = self._retrieve(imdbURL_character_main % characterID + 'bio')
        return self.cProxy.character_bio_parser.parse(cont,
                                                    getRefs=self._getRefs)

    def get_character_episodes(self, characterID):
        cont = self._retrieve(imdbURL_character_main % characterID +
                                'filmoseries')
        return self.cProxy.character_series_parser.parse(cont)

    def get_character_quotes(self, characterID):
        cont = self._retrieve(imdbURL_character_main % characterID + 'quotes')
        return self.cProxy.character_quotes_parser.parse(cont,
                                                    getRefs=self._getRefs)

    def _search_company(self, name, results):
        cont = self._get_search_content('co', name, results)
        url = self.urlOpener._last_url
        return self.scompProxy.search_company_parser.parse(cont, url=url,
                                                    results=results)['data']

    def get_company_main(self, companyID):
        cont = self._retrieve(imdbURL_company_main % companyID)
        ret = self.compProxy.company_main_parser.parse(cont)
        return ret

    def _search_keyword(self, keyword, results):
        # XXX: the IMDb web server seems to have some serious problem with
        #      non-ascii keyword.
        #      E.g.: http://akas.imdb.com/keyword/fianc%E9/
        #      will return a 500 Internal Server Error: Redirect Recursion.
        keyword = keyword.encode('utf8', 'ignore')
        try:
            cont = self._get_search_content('kw', keyword, results)
        except IMDbDataAccessError:
            self._http_logger.warn('unable to search for keyword %s', keyword,
                                    exc_info=True)
            return []
        return self.skProxy.search_keyword_parser.parse(cont, results=results)['data']

    def _get_keyword(self, keyword, results):
        keyword = keyword.encode('utf8', 'ignore')
        try:
            cont = self._retrieve(imdbURL_keyword_main % keyword)
        except IMDbDataAccessError:
            self._http_logger.warn('unable to get keyword %s', keyword,
                                    exc_info=True)
            return []
        return self.skProxy.search_moviekeyword_parser.parse(cont, results=results)['data']

    def _get_top_bottom_movies(self, kind):
        if kind == 'top':
            parser = self.topBottomProxy.top250_parser
            url = imdbURL_top250
        elif kind == 'bottom':
            parser = self.topBottomProxy.bottom100_parser
            url = imdbURL_bottom100
        else:
            return []
        cont = self._retrieve(url)
        return parser.parse(cont)['data']


