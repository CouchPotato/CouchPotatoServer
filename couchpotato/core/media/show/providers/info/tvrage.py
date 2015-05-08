from datetime import datetime
import os
import traceback

from couchpotato import Env

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.media.show.providers.base import ShowProvider
from tvrage_api import tvrage_api
from tvrage_api import tvrage_exceptions
from tvrage_api.tvrage_api import Show

log = CPLog(__name__)

autoload = 'TVRage'


class TVRage(ShowProvider):

    def __init__(self):
        # Search is handled by Trakt exclusively as search functionality has
        # been removed from TheTVDB provider as well.
        addEvent('show.info', self.getShowInfo, priority = 3)
        addEvent('season.info', self.getSeasonInfo, priority = 3)
        addEvent('episode.info', self.getEpisodeInfo, priority = 3)

        self.tvrage_api_parms = {
            'apikey': self.conf('api_key'),
            'language': 'en',
            'cache': os.path.join(Env.get('cache_dir'), 'tvrage_api')
        }
        self._setup()

    def _setup(self):
        self.tvrage = tvrage_api.TVRage(**self.tvrage_api_parms)
        self.valid_languages = self.tvrage.config['valid_languages']

    def getShow(self, identifier):
        show = None
        try:
            log.debug('Getting show: %s', identifier)
            show = self.tvrage[int(identifier)]
        except (tvrage_exceptions.tvrage_error, IOError), e:
            log.error('Failed to getShowInfo for show id "%s": %s', (identifier, traceback.format_exc()))

        return show

    def getShowInfo(self, identifiers = None):

        if not identifiers:
            # Raise exception instead? Invocation is clearly wrong!
            return None
        if 'tvrage' not in identifiers:
            # TVRage identifier unavailable, but invocation was valid.
            return None

        identifier = tryInt(identifiers['tvrage'], None)
        if identifier is None:
            # Raise exception instead? Invocation is clearly wrong!
            return None

        cache_key = 'tvrage.cache.show.%s' % identifier
        result = self.getCache(cache_key) or []
        if not result:
            show = self.getShow(identifier)
            if show is not None:
                result = self._parseShow(show)
                self.setCache(cache_key, result)

        return result

    def getSeasonInfo(self, identifiers = None, params = {}):
        """Either return a list of all seasons or a single season by number.
        identifier is the show 'id'
        """
        if not identifiers:
            # Raise exception instead? Invocation is clearly wrong!
            return None
        if 'tvrage' not in identifiers:
            # TVRage identifier unavailable, but invocation was valid.
            return None

        season_number = params.get('season_number', None)
        identifier = tryInt(identifiers['tvrage'], None)
        if identifier is None:
            # Raise exception instead? Invocation is clearly wrong!
            return None

        cache_key = 'tvrage.cache.%s.%s' % (identifier, season_number)
        log.debug('Getting TVRage SeasonInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvrage[int(identifier)]
        except (tvrage_exceptions.tvrage_error, IOError), e:
            log.error('Failed parsing TVRage SeasonInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
            return False

        result = []
        for number, season in show.items():
            if season_number is None:
                result.append(self._parseSeason(show, number, season))
            elif number == season_number:
                result = self._parseSeason(show, number, season)
                break

        self.setCache(cache_key, result)
        return result

    def getEpisodeInfo(self, identifiers = None, params = {}):
        """Either return a list of all episodes or a single episode.
        If episode_identifer contains an episode number to search for
        """
        if not identifiers:
            # Raise exception instead? Invocation is clearly wrong!
            return None
        if 'tvrage' not in identifiers:
            # TVRage identifier unavailable, but invocation was valid.
            return None

        season_number = params.get('season_number', None)
        episode_identifiers = params.get('episode_identifiers', None)
        identifier = tryInt(identifiers['tvrage'], None)
        if season_number is None:
            # Raise exception instead? Invocation is clearly wrong!
            return False
        if identifier is None:
            # season_identifier might contain the 'show id : season number'
            # since there is no tvrage id for season and we need a reference to
            # both the show id and season number.
            try:
                identifier, season_number = season_number.split(':')
                season_number = int(season_number)
                identifier = tryInt(identifier, None)
            except:
                pass

            if identifier is None:
                # Raise exception instead? Invocation is clearly wrong!
                return None

        episode_identifier = None
        if episode_identifiers:
            if 'tvrage' in episode_identifiers:
                episode_identifier = tryInt(episode_identifiers['tvrage'], None)
            if episode_identifier is None:
                return None

        cache_key = 'tvrage.cache.%s.%s.%s' % (identifier, episode_identifier, season_number)
        log.debug('Getting TVRage EpisodeInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvrage[int(identifier)]
        except (tvrage_exceptions.tvrage_error, IOError), e:
            log.error('Failed parsing TVRage EpisodeInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
            return False

        result = []
        for number, season in show.items():
            if season_number is not None and number != season_number:
                continue

            for episode in season.values():
                if episode_identifier is not None and episode['id'] == toUnicode(episode_identifier):
                    result = self._parseEpisode(episode)
                    self.setCache(cache_key, result)
                    return result
                else:
                    result.append(self._parseEpisode(episode))

        self.setCache(cache_key, result)
        return result

    def _parseShow(self, show):
        #
        # NOTE: tvrage_api mimics tvdb_api, but some information is unavailable
        #

        #
        # NOTE: show object only allows direct access via
        # show['id'], not show.get('id')
        #
        def get(name):
            return show.get(name) if not hasattr(show, 'search') else show[name]

        genres = splitString(get('genre'), '|')
        classification = get('classification') or ''
        if classification == 'Talk Shows':
            # "Talk Show" is a genre on TheTVDB.com, as these types of shows,
            # e.g. "The Tonight Show Starring Jimmy Fallon", often use
            # different naming schemes, it might be useful to the searcher if
            # it is added here.
            genres.append('Talk Show')
        if get('firstaired') is not None:
            try: year = datetime.strptime(get('firstaired'), '%Y-%m-%d').year
            except: year = None
        else:
            year = None

        show_data = {
            'identifiers': {
              'tvrage': tryInt(get('id')),
            },
            'type': 'show',
            'titles': [get('seriesname')],
            'images': {
                'poster': [],
                'backdrop': [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'year': year,
            'genres': genres,
            'network': get('network'),
            'air_day': (get('airs_dayofweek') or '').lower(),
            'air_time': self.parseTime(get('airs_time')),
            'firstaired': get('firstaired'),
            'runtime': tryInt(get('runtime')),
            'status': get('status'),
        }

        show_data = dict((k, v) for k, v in show_data.iteritems() if v)

        # Only load season info when available
        if type(show) == Show:

            # Parse season and episode data
            show_data['seasons'] = {}

            for season_nr in show:
                season = self._parseSeason(show, season_nr, show[season_nr])
                season['episodes'] = {}

                for episode_nr in show[season_nr]:
                    season['episodes'][episode_nr] = self._parseEpisode(show[season_nr][episode_nr])

                show_data['seasons'][season_nr] = season

        return show_data

    def _parseSeason(self, show, number, season):

        season_data = {
            'number': tryInt(number),
        }

        season_data = dict((k, v) for k, v in season_data.iteritems() if v)
        return season_data

    def _parseEpisode(self, episode):

        def get(name, default = None):
            return episode.get(name, default)

        poster = get('filename', [])

        episode_data = {
            'number': tryInt(get('episodenumber')),
            'absolute_number': tryInt(get('absolute_number')),
            'identifiers': {
                'tvrage': tryInt(episode['id'])
            },
            'type': 'episode',
            'titles': [get('episodename')] if get('episodename') else [],
            'images': {
                'poster': [poster] if poster else [],
            },
            'released': get('firstaired'),
            'firstaired': get('firstaired'),
            'language': get('language'),
        }

        episode_data = dict((k, v) for k, v in episode_data.iteritems() if v)
        return episode_data

    def parseTime(self, time):
        return time
