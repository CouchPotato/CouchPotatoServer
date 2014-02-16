#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: tmdb_api.py    Simple-to-use Python interface to TMDB's API v3
# Python Library
# Author: Raymond Wagner
# Purpose: This Python library is intended to provide a series of classes
#          and methods for search and retrieval of text metadata and image
#          URLs from TMDB.
#          Preliminary API specifications can be found at
#          http://help.themoviedb.org/kb/api/about-3
# License: Creative Commons GNU GPL v2
# (http://creativecommons.org/licenses/GPL/2.0/)
#-----------------------

__title__ = ("tmdb_api - Simple-to-use Python interface to TMDB's API v3 " +
            "(www.themoviedb.org)")
__author__ = "Raymond Wagner"
__purpose__ = """
This Python library is intended to provide a series of classes and methods
for search and retrieval of text metadata and image URLs from TMDB.
Preliminary API specifications can be found at
http://help.themoviedb.org/kb/api/about-3"""

__version__ = "v0.7.0"
# 0.1.0  Initial development
# 0.2.0  Add caching mechanism for API queries
# 0.2.1  Temporary work around for broken search paging
# 0.3.0  Rework backend machinery for managing OO interface to results
# 0.3.1  Add collection support
# 0.3.2  Remove MythTV key from results.py
# 0.3.3  Add functional language support
# 0.3.4  Re-enable search paging
# 0.3.5  Add methods for grabbing current, popular, and top rated movies
# 0.3.6  Rework paging mechanism
# 0.3.7  Generalize caching mechanism, and allow controllability
# 0.4.0  Add full locale support (language and country) and optional fall through
# 0.4.1  Add custom classmethod for dealing with IMDB movie IDs
# 0.4.2  Improve cache file selection for Windows systems
# 0.4.3  Add a few missed Person properties
# 0.4.4  Add support for additional Studio information
# 0.4.5  Add locale fallthrough for images and alternate titles
# 0.4.6  Add slice support for search results
# 0.5.0  Rework cache framework and improve file cache performance
# 0.6.0  Add user authentication support
# 0.6.1  Add adult filtering for people searches
# 0.6.2  Add similar movie search for Movie objects
# 0.6.3  Add Studio search
# 0.6.4  Add Genre list and associated Movie search
# 0.6.5  Prevent data from being blanked out by subsequent queries
# 0.6.6  Turn date processing errors into mutable warnings
# 0.6.7  Add support for searching by year
# 0.6.8  Add support for collection images
# 0.6.9  Correct Movie image language filtering
# 0.6.10 Add upcoming movie classmethod
# 0.6.11 Fix URL for top rated Movie query
# 0.6.12 Add support for Movie watchlist query and editing
# 0.6.13 Fix URL for rating Movies
# 0.6.14 Add support for Lists
# 0.6.15 Add ability to search Collections
# 0.6.16 Make absent primary images return None (previously u'')
# 0.6.17 Add userrating/votes to Image, add overview to Collection, remove
#           releasedate sorting from Collection Movies
# 0.7.0  Add support for television series data

from request import set_key, Request
from util import Datapoint, Datalist, Datadict, Element, NameRepr, SearchRepr
from pager import PagedRequest
from locales import get_locale, set_locale
from tmdb_auth import get_session, set_session
from tmdb_exceptions import *

import json
import urllib
import urllib2
import datetime

DEBUG = False


def process_date(datestr):
    try:
        return datetime.date(*[int(x) for x in datestr.split('-')])
    except (TypeError, ValueError):
        import sys
        import warnings
        import traceback
        _,_,tb = sys.exc_info()
        f,l,_,_ = traceback.extract_tb(tb)[-1]
        warnings.warn_explicit(('"{0}" is not a supported date format. ' +
                                'Please fix upstream data at ' +
                                'http://www.themoviedb.org.'
                               ).format(datestr), Warning, f, l)
        return None


class Configuration(Element):
    images = Datapoint('images')

    def _populate(self):
        return Request('configuration')

Configuration = Configuration()


class Account(NameRepr, Element):
    def _populate(self):
        return Request('account', session_id=self._session.sessionid)

    id = Datapoint('id')
    adult = Datapoint('include_adult')
    country = Datapoint('iso_3166_1')
    language = Datapoint('iso_639_1')
    name = Datapoint('name')
    username = Datapoint('username')

    @property
    def locale(self):
        return get_locale(self.language, self.country)


def searchMovie(query, locale=None, adult=False, year=None):
    kwargs = {'query': query, 'include_adult': adult}
    if year is not None:
        try:
            kwargs['year'] = year.year
        except AttributeError:
            kwargs['year'] = year
    return MovieSearchResult(Request('search/movie', **kwargs), locale=locale)


def searchMovieWithYear(query, locale=None, adult=False):
    year = None
    if (len(query) > 6) and (query[-1] == ')') and (query[-6] == '('):
        # simple syntax check, no need for regular expression
        try:
            year = int(query[-5:-1])
        except ValueError:
            pass
        else:
            if 1885 < year < 2050:
                # strip out year from search
                query = query[:-7]
            else:
                # sanity check on resolved year failed, pass through
                year = None
    return searchMovie(query, locale, adult, year)


class MovieSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name = None
    def __init__(self, request, locale=None):
        if locale is None:
            locale = get_locale()
        super(MovieSearchResult, self).__init__(
                    request.new(language=locale.language),
                    lambda x: Movie(raw=x, locale=locale))

def searchSeries(query, first_air_date_year=None, search_type=None, locale=None):
    return SeriesSearchResult(
        Request('search/tv', query=query, first_air_date_year=first_air_date_year, search_type=search_type),
        locale=locale)


class SeriesSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name = None
    def __init__(self, request, locale=None):
        if locale is None:
            locale = get_locale()
        super(SeriesSearchResult, self).__init__(
                    request.new(language=locale.language),
                    lambda x: Series(raw=x, locale=locale))

def searchPerson(query, adult=False):
    return PeopleSearchResult(Request('search/person', query=query,
                                      include_adult=adult))


class PeopleSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name = None
    def __init__(self, request):
        super(PeopleSearchResult, self).__init__(
                    request, lambda x: Person(raw=x))


def searchStudio(query):
    return StudioSearchResult(Request('search/company', query=query))


class StudioSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name = None
    def __init__(self, request):
        super(StudioSearchResult, self).__init__(
                    request, lambda x: Studio(raw=x))


def searchList(query, adult=False):
    ListSearchResult(Request('search/list', query=query, include_adult=adult))


class ListSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name = None
    def __init__(self, request):
        super(ListSearchResult, self).__init__(
                    request, lambda x: List(raw=x))


def searchCollection(query, locale=None):
    return CollectionSearchResult(Request('search/collection', query=query),
                           locale=locale)


class CollectionSearchResult(SearchRepr, PagedRequest):
    """Stores a list of search matches."""
    _name=None
    def __init__(self, request, locale=None):
        if locale is None:
            locale = get_locale()
        super(CollectionSearchResult, self).__init__(
                    request.new(language=locale.language),
                    lambda x: Collection(raw=x, locale=locale))


class Image(Element):
    filename = Datapoint('file_path', initarg=1,
                         handler=lambda x: x.lstrip('/'))
    aspectratio = Datapoint('aspect_ratio')
    height = Datapoint('height')
    width = Datapoint('width')
    language = Datapoint('iso_639_1')
    userrating = Datapoint('vote_average')
    votes = Datapoint('vote_count')

    def sizes(self):
        return ['original']

    def geturl(self, size='original'):
        if size not in self.sizes():
            raise TMDBImageSizeError
        url = Configuration.images['secure_base_url'].rstrip('/')
        return url+'/{0}/{1}'.format(size, self.filename)

    # sort preferring locale's language, but keep remaining ordering consistent
    def __lt__(self, other):
        if not isinstance(other, Image):
            return False
        return (self.language == self._locale.language) \
                and (self.language != other.language)

    def __gt__(self, other):
        if not isinstance(other, Image):
            return True
        return (self.language != other.language) \
                and (other.language == self._locale.language)

    # direct match for comparison
    def __eq__(self, other):
        if not isinstance(other, Image):
            return False
        return self.filename == other.filename

    # special handling for boolean to see if exists
    def __nonzero__(self):
        if len(self.filename) == 0:
            return False
        return True

    def __repr__(self):
        # BASE62 encoded filename, no need to worry about unicode
        return u"<{0.__class__.__name__} '{0.filename}'>".format(self)


class Backdrop(Image):
    def sizes(self):
        return Configuration.images['backdrop_sizes']


class Poster(Image):
    def sizes(self):
        return Configuration.images['poster_sizes']


class Profile(Image):
    def sizes(self):
        return Configuration.images['profile_sizes']


class Logo(Image):
    def sizes(self):
        return Configuration.images['logo_sizes']


class AlternateTitle(Element):
    country     = Datapoint('iso_3166_1')
    title       = Datapoint('title')

    # sort preferring locale's country, but keep remaining ordering consistent
    def __lt__(self, other):
        return (self.country == self._locale.country) \
                and (self.country != other.country)

    def __gt__(self, other):
        return (self.country != other.country) \
                and (other.country == self._locale.country)

    def __eq__(self, other):
        return self.country == other.country

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.title}' ({0.country})>"\
               .format(self).encode('utf-8')


class Person(Element):
    id = Datapoint('id', initarg=1)
    name = Datapoint('name')
    biography = Datapoint('biography')
    dayofbirth = Datapoint('birthday', default=None, handler=process_date)
    dayofdeath = Datapoint('deathday', default=None, handler=process_date)
    homepage = Datapoint('homepage')
    birthplace = Datapoint('place_of_birth')
    profile = Datapoint('profile_path', handler=Profile,
                        raw=False, default=None)
    adult = Datapoint('adult')
    aliases = Datalist('also_known_as')

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}'>"\
                            .format(self).encode('utf-8')

    def _populate(self):
        return Request('person/{0}'.format(self.id))

    def _populate_credits(self):
        return Request('person/{0}/credits'.format(self.id),
                       language=self._locale.language)
    def _populate_images(self):
        return Request('person/{0}/images'.format(self.id))

    roles = Datalist('cast', handler=lambda x: ReverseCast(raw=x),
                     poller=_populate_credits)
    crew = Datalist('crew', handler=lambda x: ReverseCrew(raw=x),
                    poller=_populate_credits)
    profiles = Datalist('profiles', handler=Profile, poller=_populate_images)


class Cast(Person):
    character = Datapoint('character')
    order = Datapoint('order')

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}' as '{0.character}'>"\
               .format(self).encode('utf-8')


class Crew(Person):
    job = Datapoint('job')
    department = Datapoint('department')

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}','{0.job}'>"\
               .format(self).encode('utf-8')


class Keyword(Element):
    id   = Datapoint('id')
    name = Datapoint('name')

    def __repr__(self):
        return u"<{0.__class__.__name__} {0.name}>"\
               .format(self).encode('utf-8')


class Release(Element):
    certification = Datapoint('certification')
    country = Datapoint('iso_3166_1')
    releasedate = Datapoint('release_date', handler=process_date)
    def __repr__(self):
        return u"<{0.__class__.__name__} {0.country}, {0.releasedate}>"\
               .format(self).encode('utf-8')


class Trailer(Element):
    name = Datapoint('name')
    size = Datapoint('size')
    source = Datapoint('source')


class YoutubeTrailer(Trailer):
    def geturl(self):
        return "http://www.youtube.com/watch?v={0}".format(self.source)

    def __repr__(self):
        # modified BASE64 encoding, no need to worry about unicode
        return u"<{0.__class__.__name__} '{0.name}'>".format(self)


class AppleTrailer(Element):
    name = Datapoint('name')
    sources = Datadict('sources', handler=Trailer, attr='size')

    def sizes(self):
        return self.sources.keys()

    def geturl(self, size=None):
        if size is None:
            # sort assuming ###p format for now, take largest resolution
            size = str(sorted(
                        [int(size[:-1]) for size in self.sources]
                        )[-1]) + 'p'
        return self.sources[size].source

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}'>".format(self)


class Translation(Element):
    name = Datapoint('name')
    language = Datapoint('iso_639_1')
    englishname = Datapoint('english_name')

    def __repr__(self):
        return u"<{0.__class__.__name__} '{0.name}' ({0.language})>"\
               .format(self).encode('utf-8')


class Genre(NameRepr, Element):
    id = Datapoint('id')
    name = Datapoint('name')

    def _populate_movies(self):
        return Request('genre/{0}/movies'.format(self.id), \
                       language=self._locale.language)

    @property
    def movies(self):
        if 'movies' not in self._data:
            search = MovieSearchResult(self._populate_movies(), \
                                       locale=self._locale)
            search._name = "{0.name} Movies".format(self)
            self._data['movies'] = search
        return self._data['movies']

    @classmethod
    def getAll(cls, locale=None):
        class GenreList(Element):
            genres = Datalist('genres', handler=Genre)

            def _populate(self):
                return Request('genre/list', language=self._locale.language)
        return GenreList(locale=locale).genres


class Studio(NameRepr, Element):
    id = Datapoint('id', initarg=1)
    name = Datapoint('name')
    description = Datapoint('description')
    headquarters = Datapoint('headquarters')
    logo = Datapoint('logo_path', handler=Logo, raw=False, default=None)
    # FIXME: manage not-yet-defined handlers in a way that will propogate
    #        locale information properly
    parent = Datapoint('parent_company', handler=lambda x: Studio(raw=x))

    def _populate(self):
        return Request('company/{0}'.format(self.id))

    def _populate_movies(self):
        return Request('company/{0}/movies'.format(self.id),
                       language=self._locale.language)

    # FIXME: add a cleaner way of adding types with no additional processing
    @property
    def movies(self):
        if 'movies' not in self._data:
            search = MovieSearchResult(self._populate_movies(),
                                       locale=self._locale)
            search._name = "{0.name} Movies".format(self)
            self._data['movies'] = search
        return self._data['movies']


class Country(NameRepr, Element):
    code = Datapoint('iso_3166_1')
    name = Datapoint('name')


class Language(NameRepr, Element):
    code = Datapoint('iso_639_1')
    name = Datapoint('name')


class Movie(Element):
    @classmethod
    def latest(cls):
        req = Request('latest/movie')
        req.lifetime = 600
        return cls(raw=req.readJSON())

    @classmethod
    def nowplaying(cls, locale=None):
        res = MovieSearchResult(Request('movie/now-playing'), locale=locale)
        res._name = 'Now Playing'
        return res

    @classmethod
    def mostpopular(cls, locale=None):
        res = MovieSearchResult(Request('movie/popular'), locale=locale)
        res._name = 'Popular'
        return res

    @classmethod
    def toprated(cls, locale=None):
        res = MovieSearchResult(Request('movie/top_rated'), locale=locale)
        res._name = 'Top Rated'
        return res

    @classmethod
    def upcoming(cls, locale=None):
        res = MovieSearchResult(Request('movie/upcoming'), locale=locale)
        res._name = 'Upcoming'
        return res

    @classmethod
    def favorites(cls, session=None):
        if session is None:
            session = get_session()
        account = Account(session=session)
        res = MovieSearchResult(
                    Request('account/{0}/favorite_movies'.format(account.id),
                            session_id=session.sessionid))
        res._name = "Favorites"
        return res

    @classmethod
    def ratedmovies(cls, session=None):
        if session is None:
            session = get_session()
        account = Account(session=session)
        res = MovieSearchResult(
                    Request('account/{0}/rated_movies'.format(account.id),
                            session_id=session.sessionid))
        res._name = "Movies You Rated"
        return res

    @classmethod
    def watchlist(cls, session=None):
        if session is None:
            session = get_session()
        account = Account(session=session)
        res = MovieSearchResult(
                    Request('account/{0}/movie_watchlist'.format(account.id),
                            session_id=session.sessionid))
        res._name = "Movies You're Watching"
        return res

    @classmethod
    def fromIMDB(cls, imdbid, locale=None):
        try:
            # assume string
            if not imdbid.startswith('tt'):
                imdbid = "tt{0:0>7}".format(imdbid)
        except AttributeError:
            # assume integer
            imdbid = "tt{0:0>7}".format(imdbid)
        if locale is None:
            locale = get_locale()
        movie = cls(imdbid, locale=locale)
        movie._populate()
        return movie

    id = Datapoint('id', initarg=1)
    title = Datapoint('title')
    originaltitle = Datapoint('original_title')
    tagline = Datapoint('tagline')
    overview = Datapoint('overview')
    runtime = Datapoint('runtime')
    budget = Datapoint('budget')
    revenue = Datapoint('revenue')
    releasedate = Datapoint('release_date', handler=process_date)
    homepage = Datapoint('homepage')
    imdb = Datapoint('imdb_id')

    backdrop = Datapoint('backdrop_path', handler=Backdrop,
                         raw=False, default=None)
    poster = Datapoint('poster_path', handler=Poster,
                       raw=False, default=None)

    popularity = Datapoint('popularity')
    userrating = Datapoint('vote_average')
    votes = Datapoint('vote_count')

    adult = Datapoint('adult')
    collection = Datapoint('belongs_to_collection', handler=lambda x: \
                                                        Collection(raw=x))
    genres = Datalist('genres', handler=Genre)
    studios = Datalist('production_companies', handler=Studio)
    countries = Datalist('production_countries', handler=Country)
    languages = Datalist('spoken_languages', handler=Language)

    def _populate(self):
        return Request('movie/{0}'.format(self.id), \
                       language=self._locale.language)

    def _populate_titles(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['country'] = self._locale.country
        return Request('movie/{0}/alternative_titles'.format(self.id),
                       **kwargs)

    def _populate_cast(self):
        return Request('movie/{0}/casts'.format(self.id))

    def _populate_images(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['language'] = self._locale.language
        return Request('movie/{0}/images'.format(self.id), **kwargs)

    def _populate_keywords(self):
        return Request('movie/{0}/keywords'.format(self.id))

    def _populate_releases(self):
        return Request('movie/{0}/releases'.format(self.id))

    def _populate_trailers(self):
        return Request('movie/{0}/trailers'.format(self.id),
                            language=self._locale.language)

    def _populate_translations(self):
        return Request('movie/{0}/translations'.format(self.id))

    alternate_titles = Datalist('titles', handler=AlternateTitle, \
                                poller=_populate_titles, sort=True)

    # FIXME: this data point will need to be changed to 'credits' at some point
    cast = Datalist('cast', handler=Cast,
                    poller=_populate_cast, sort='order')

    crew = Datalist('crew', handler=Crew, poller=_populate_cast)
    backdrops = Datalist('backdrops', handler=Backdrop,
                         poller=_populate_images, sort=True)
    posters = Datalist('posters', handler=Poster,
                       poller=_populate_images, sort=True)
    keywords = Datalist('keywords', handler=Keyword,
                        poller=_populate_keywords)
    releases = Datadict('countries', handler=Release,
                        poller=_populate_releases, attr='country')
    youtube_trailers = Datalist('youtube', handler=YoutubeTrailer,
                                poller=_populate_trailers)
    apple_trailers = Datalist('quicktime', handler=AppleTrailer,
                              poller=_populate_trailers)
    translations = Datalist('translations', handler=Translation,
                            poller=_populate_translations)

    def setFavorite(self, value):
        req = Request('account/{0}/favorite'.format(
                        Account(session=self._session).id),
                      session_id=self._session.sessionid)
        req.add_data({'movie_id': self.id,
                      'favorite': str(bool(value)).lower()})
        req.lifetime = 0
        req.readJSON()

    def setRating(self, value):
        if not (0 <= value <= 10):
            raise TMDBError("Ratings must be between '0' and '10'.")
        req = Request('movie/{0}/rating'.format(self.id),
                      session_id=self._session.sessionid)
        req.lifetime = 0
        req.add_data({'value':value})
        req.readJSON()

    def setWatchlist(self, value):
        req = Request('account/{0}/movie_watchlist'.format(
                        Account(session=self._session).id),
                      session_id=self._session.sessionid)
        req.lifetime = 0
        req.add_data({'movie_id': self.id,
                      'movie_watchlist': str(bool(value)).lower()})
        req.readJSON()

    def getSimilar(self):
        return self.similar

    @property
    def similar(self):
        res = MovieSearchResult(Request(
                                 'movie/{0}/similar_movies'.format(self.id)),
                                 locale=self._locale)
        res._name = 'Similar to {0}'.format(self._printable_name())
        return res

    @property
    def lists(self):
        res = ListSearchResult(Request('movie/{0}/lists'.format(self.id)))
        res._name = "Lists containing {0}".format(self._printable_name())
        return res

    def _printable_name(self):
        if self.title is not None:
            s = u"'{0}'".format(self.title)
        elif self.originaltitle is not None:
            s = u"'{0}'".format(self.originaltitle)
        else:
            s = u"'No Title'"
        if self.releasedate:
            s = u"{0} ({1})".format(s, self.releasedate.year)
        return s

    def __repr__(self):
        return u"<{0} {1}>".format(self.__class__.__name__,
                                   self._printable_name()).encode('utf-8')


class ReverseCast( Movie ):
    character = Datapoint('character')

    def __repr__(self):
        return (u"<{0.__class__.__name__} '{0.character}' on {1}>"
                .format(self, self._printable_name()).encode('utf-8'))


class ReverseCrew( Movie ):
    department = Datapoint('department')
    job = Datapoint('job')

    def __repr__(self):
        return (u"<{0.__class__.__name__} '{0.job}' for {1}>"
                .format(self, self._printable_name()).encode('utf-8'))


class Collection(NameRepr, Element):
    id = Datapoint('id', initarg=1)
    name = Datapoint('name')
    backdrop = Datapoint('backdrop_path', handler=Backdrop, \
                         raw=False, default=None)
    poster = Datapoint('poster_path', handler=Poster, raw=False, default=None)
    members = Datalist('parts', handler=Movie)
    overview = Datapoint('overview')

    def _populate(self):
        return Request('collection/{0}'.format(self.id),
                       language=self._locale.language)

    def _populate_images(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['language'] = self._locale.language
        return Request('collection/{0}/images'.format(self.id), **kwargs)

    backdrops = Datalist('backdrops', handler=Backdrop,
                         poller=_populate_images, sort=True)
    posters = Datalist('posters', handler=Poster,
                       poller=_populate_images, sort=True)

class List(NameRepr, Element):
    id = Datapoint('id', initarg=1)
    name = Datapoint('name')
    author = Datapoint('created_by')
    description = Datapoint('description')
    favorites = Datapoint('favorite_count')
    language = Datapoint('iso_639_1')
    count = Datapoint('item_count')
    poster = Datapoint('poster_path', handler=Poster, raw=False, default=None)
    members = Datalist('items', handler=Movie)

    def _populate(self):
        return Request('list/{0}'.format(self.id))

class Network(NameRepr,Element):
    id = Datapoint('id', initarg=1)
    name = Datapoint('name')

class Episode(NameRepr, Element):
    episode_number = Datapoint('episode_number', initarg=3)
    season_number = Datapoint('season_number', initarg=2)
    series_id = Datapoint('series_id', initarg=1)
    air_date = Datapoint('air_date', handler=process_date)
    overview = Datapoint('overview')
    name = Datapoint('name')
    userrating = Datapoint('vote_average')
    votes = Datapoint('vote_count')
    id = Datapoint('id')
    production_code = Datapoint('production_code')
    still = Datapoint('still_path', handler=Backdrop, raw=False, default=None)

    def _populate(self):
        return Request('tv/{0}/season/{1}/episode/{2}'.format(self.series_id, self.season_number, self.episode_number),
                       language=self._locale.language)

    def _populate_cast(self):
        return Request('tv/{0}/season/{1}/episode/{2}/credits'.format(
            self.series_id, self.season_number, self.episode_number),
                       language=self._locale.language)

    def _populate_external_ids(self):
        return Request('tv/{0}/season/{1}/episode/{2}/external_ids'.format(
            self.series_id, self.season_number, self.episode_number))

    def _populate_images(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['language'] = self._locale.language
        return Request('tv/{0}/season/{1}/episode/{2}/images'.format(
            self.series_id, self.season_number, self.episode_number), **kwargs)

    cast = Datalist('cast', handler=Cast,
                    poller=_populate_cast, sort='order')
    guest_stars = Datalist('guest_stars', handler=Cast,
                    poller=_populate_cast, sort='order')
    crew = Datalist('crew', handler=Crew, poller=_populate_cast)
    imdb_id = Datapoint('imdb_id', poller=_populate_external_ids)
    freebase_id = Datapoint('freebase_id', poller=_populate_external_ids)
    freebase_mid = Datapoint('freebase_mid', poller=_populate_external_ids)
    tvdb_id = Datapoint('tvdb_id', poller=_populate_external_ids)
    tvrage_id = Datapoint('tvrage_id', poller=_populate_external_ids)
    stills = Datalist('stills', handler=Backdrop, poller=_populate_images, sort=True)

class Season(NameRepr, Element):
    season_number = Datapoint('season_number', initarg=2)
    series_id = Datapoint('series_id', initarg=1)
    id = Datapoint('id')
    air_date = Datapoint('air_date', handler=process_date)
    poster = Datapoint('poster_path', handler=Poster, raw=False, default=None)
    overview = Datapoint('overview')
    name = Datapoint('name')
    episodes = Datadict('episodes', attr='episode_number', handler=Episode,
                        passthrough={'series_id': 'series_id', 'season_number': 'season_number'})

    def _populate(self):
        return Request('tv/{0}/season/{1}'.format(self.series_id, self.season_number),
                       language=self._locale.language)

    def _populate_images(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['language'] = self._locale.language
        return Request('tv/{0}/season/{1}/images'.format(self.series_id, self.season_number), **kwargs)

    def _populate_external_ids(self):
        return Request('tv/{0}/season/{1}/external_ids'.format(self.series_id, self.season_number))

    posters = Datalist('posters', handler=Poster,
                       poller=_populate_images, sort=True)

    freebase_id = Datapoint('freebase_id', poller=_populate_external_ids)
    freebase_mid = Datapoint('freebase_mid', poller=_populate_external_ids)
    tvdb_id = Datapoint('tvdb_id', poller=_populate_external_ids)
    tvrage_id = Datapoint('tvrage_id', poller=_populate_external_ids)

class Series(NameRepr, Element):
    id = Datapoint('id', initarg=1)
    backdrop = Datapoint('backdrop_path', handler=Backdrop, raw=False, default=None)
    authors = Datalist('created_by', handler=Person)
    episode_run_times = Datalist('episode_run_time')
    first_air_date = Datapoint('first_air_date', handler=process_date)
    last_air_date = Datapoint('last_air_date', handler=process_date)
    genres = Datalist('genres', handler=Genre)
    homepage = Datapoint('homepage')
    in_production = Datapoint('in_production')
    languages = Datalist('languages')
    origin_countries = Datalist('origin_country')
    name = Datapoint('name')
    original_name = Datapoint('original_name')
    number_of_episodes = Datapoint('number_of_episodes')
    number_of_seasons = Datapoint('number_of_seasons')
    overview = Datapoint('overview')
    popularity = Datapoint('popularity')
    status = Datapoint('status')
    userrating = Datapoint('vote_average')
    votes = Datapoint('vote_count')
    poster = Datapoint('poster_path', handler=Poster, raw=False, default=None)
    networks = Datalist('networks', handler=Network)
    seasons = Datadict('seasons', attr='season_number', handler=Season, passthrough={'id': 'series_id'})

    def _populate(self):
        return Request('tv/{0}'.format(self.id),
                       language=self._locale.language)

    def _populate_cast(self):
        return Request('tv/{0}/credits'.format(self.id))

    def _populate_images(self):
        kwargs = {}
        if not self._locale.fallthrough:
            kwargs['language'] = self._locale.language
        return Request('tv/{0}/images'.format(self.id), **kwargs)

    def _populate_external_ids(self):
        return Request('tv/{0}/external_ids'.format(self.id))

    cast = Datalist('cast', handler=Cast,
                    poller=_populate_cast, sort='order')
    crew = Datalist('crew', handler=Crew, poller=_populate_cast)
    backdrops = Datalist('backdrops', handler=Backdrop,
                         poller=_populate_images, sort=True)
    posters = Datalist('posters', handler=Poster,
                       poller=_populate_images, sort=True)

    imdb_id = Datapoint('imdb_id', poller=_populate_external_ids)
    freebase_id = Datapoint('freebase_id', poller=_populate_external_ids)
    freebase_mid = Datapoint('freebase_mid', poller=_populate_external_ids)
    tvdb_id = Datapoint('tvdb_id', poller=_populate_external_ids)
    tvrage_id = Datapoint('tvrage_id', poller=_populate_external_ids)
