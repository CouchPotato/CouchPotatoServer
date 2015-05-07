from datetime import datetime
import os
import traceback

from couchpotato import Env

from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.media.show.providers.base import ShowProvider
from tvdb_api import tvdb_exceptions
from tvdb_api.tvdb_api import Tvdb, Show

log = CPLog(__name__)

autoload = 'TheTVDb'


class TheTVDb(ShowProvider):

    # TODO: Consider grabbing zips to put less strain on tvdb
    # TODO: Unicode stuff (check)
    # TODO: Notigy frontend on error (tvdb down at monent)
    # TODO: Expose apikey in setting so it can be changed by user

    def __init__(self):
        addEvent('show.info', self.getShowInfo, priority = 1)
        addEvent('season.info', self.getSeasonInfo, priority = 1)
        addEvent('episode.info', self.getEpisodeInfo, priority = 1)

        self.tvdb_api_parms = {
            'apikey': self.conf('api_key'),
            'banners': True,
            'language': 'en',
            'cache': os.path.join(Env.get('cache_dir'), 'thetvdb_api'),
        }
        self._setup()

    def _setup(self):
        self.tvdb = Tvdb(**self.tvdb_api_parms)
        self.valid_languages = self.tvdb.config['valid_languages']

    def getShow(self, identifier = None):
        show = None
        try:
            log.debug('Getting show: %s', identifier)
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed to getShowInfo for show id "%s": %s', (identifier, traceback.format_exc()))
            return None

        return show

    def getShowInfo(self, identifiers = None):
        """

        @param identifiers: dict with identifiers per provider
        @return: Full show info including season and episode info
        """

        if not identifiers or not identifiers.get('thetvdb'):
            return None

        identifier = tryInt(identifiers.get('thetvdb'))

        cache_key = 'thetvdb.cache.show.%s' % identifier
        result = None #self.getCache(cache_key)
        if result:
            return result

        show = self.getShow(identifier = identifier)
        if show:
            result = self._parseShow(show)
            self.setCache(cache_key, result)

        return result or {}

    def getSeasonInfo(self, identifiers = None, params = {}):
        """Either return a list of all seasons or a single season by number.
        identifier is the show 'id'
        """
        if not identifiers or not identifiers.get('thetvdb'):
            return None

        season_number = params.get('season_number', None)
        identifier = tryInt(identifiers.get('thetvdb'))

        cache_key = 'thetvdb.cache.%s.%s' % (identifier, season_number)
        log.debug('Getting SeasonInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed parsing TheTVDB SeasonInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
            return False

        result = []
        for number, season in show.items():
            if season_number is not None and number == season_number:
                result = self._parseSeason(show, number, season)
                self.setCache(cache_key, result)
                return result
            else:
                result.append(self._parseSeason(show, number, season))

        self.setCache(cache_key, result)
        return result

    def getEpisodeInfo(self, identifier = None, params = {}):
        """Either return a list of all episodes or a single episode.
        If episode_identifer contains an episode number to search for
        """
        season_number = self.getIdentifier(params.get('season_number', None))
        episode_identifier = self.getIdentifier(params.get('episode_identifiers', None))
        identifier = self.getIdentifier(identifier)

        if not identifier and season_number is None:
            return False

        # season_identifier must contain the 'show id : season number' since there is no tvdb id
        # for season and we need a reference to both the show id and season number
        if not identifier and season_number:
            try:
                identifier, season_number = season_number.split(':')
                season_number = int(season_number)
            except: return None

        cache_key = 'thetvdb.cache.%s.%s.%s' % (identifier, episode_identifier, season_number)
        log.debug('Getting EpisodeInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed parsing TheTVDB EpisodeInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
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

    def getIdentifier(self, value):
        if type(value) is dict:
            return value.get('thetvdb')

        return value

    def _parseShow(self, show):

        #
        # NOTE: show object only allows direct access via
        # show['id'], not show.get('id')
        #
        def get(name):
            return show.get(name) if not hasattr(show, 'search') else show[name]

        ## Images
        poster = get('poster')
        backdrop = get('fanart')

        genres = splitString(get('genre'), '|')
        if get('firstaired') is not None:
            try: year = datetime.strptime(get('firstaired'), '%Y-%m-%d').year
            except: year = None
        else:
            year = None

        show_data = {
            'identifiers': {
              'thetvdb': tryInt(get('id')),
              'imdb': get('imdb_id'),
              'zap2it': get('zap2it_id'),
            },
            'type': 'show',
            'titles': [get('seriesname')],
            'images': {
                'poster': [poster] if poster else [],
                'backdrop': [backdrop] if backdrop else [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'year': year,
            'genres': genres,
            'network': get('network'),
            'plot': get('overview'),
            'networkid': get('networkid'),
            'air_day': (get('airs_dayofweek') or '').lower(),
            'air_time': self.parseTime(get('airs_time')),
            'firstaired': get('firstaired'),
            'runtime': tryInt(get('runtime')),
            'contentrating': get('contentrating'),
            'rating': {},
            'actors': splitString(get('actors'), '|'),
            'status': get('status'),
            'language': get('language'),
        }

        if tryFloat(get('rating')):
            show_data['rating']['thetvdb'] = [tryFloat(get('rating')), tryInt(get('ratingcount'))],

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

        # Add alternative titles
        # try:
        #     raw = self.tvdb.search(show['seriesname'])
        #     if raw:
        #         for show_info in raw:
        #             print show_info
        #             if show_info['id'] == show_data['id'] and show_info.get('aliasnames', None):
        #                 for alt_name in show_info['aliasnames'].split('|'):
        #                     show_data['titles'].append(toUnicode(alt_name))
        # except (tvdb_exceptions.tvdb_error, IOError), e:
        #     log.error('Failed searching TheTVDB for "%s": %s', (show['seriesname'], traceback.format_exc()))

        return show_data

    def _parseSeason(self, show, number, season):
        """
        contains no data
        """

        poster = []
        try:
            temp_poster = {}
            for id, data in show.data['_banners']['season']['season'].items():
                if data.get('season') == str(number) and data.get('language') == self.tvdb_api_parms['language']:
                    temp_poster[tryFloat(data.get('rating')) * tryInt(data.get('ratingcount'))] = data.get('_bannerpath')
                    #break
            poster.append(temp_poster[sorted(temp_poster, reverse = True)[0]])
        except:
            pass

        season_data = {
            'identifiers': {
                'thetvdb': show['id'] if show.get('id') else show[number][1]['seasonid']
            },
            'number': tryInt(number),
            'images': {
                'poster': poster,
            },
        }

        season_data = dict((k, v) for k, v in season_data.iteritems() if v)
        return season_data

    def _parseEpisode(self, episode):
        """
        ('episodenumber', u'1'),
        ('thumb_added', None),
        ('rating', u'7.7'),
        ('overview',
         u'Experienced waitress Max Black meets her new co-worker, former rich-girl Caroline Channing, and puts her skills to the test at an old but re-emerging Brooklyn diner. Despite her initial distaste for Caroline, Max eventually softens and the two team up for a new business venture.'),
        ('dvd_episodenumber', None),
        ('dvd_discid', None),
        ('combined_episodenumber', u'1'),
        ('epimgflag', u'7'),
        ('id', u'4099506'),
        ('seasonid', u'465948'),
        ('thumb_height', u'225'),
        ('tms_export', u'1374789754'),
        ('seasonnumber', u'1'),
        ('writer', u'|Michael Patrick King|Whitney Cummings|'),
        ('lastupdated', u'1371420338'),
        ('filename', u'http://thetvdb.com/banners/episodes/248741/4099506.jpg'),
        ('absolute_number', u'1'),
        ('ratingcount', u'102'),
        ('combined_season', u'1'),
        ('thumb_width', u'400'),
        ('imdb_id', u'tt1980319'),
        ('director', u'James Burrows'),
        ('dvd_chapter', None),
        ('dvd_season', None),
        ('gueststars',
         u'|Brooke Lyons|Noah Mills|Shoshana Bush|Cale Hartmann|Adam Korson|Alex Enriquez|Matt Cook|Bill Parks|Eugene Shaw|Sergey Brusilovsky|Greg Lewis|Cocoa Brown|Nick Jameson|'),
        ('seriesid', u'248741'),
        ('language', u'en'),
        ('productioncode', u'296793'),
        ('firstaired', u'2011-09-19'),
        ('episodename', u'Pilot')]
        """

        def get(name, default = None):
            return episode.get(name, default)

        poster = get('filename', [])

        episode_data = {
            'number': tryInt(get('episodenumber')),
            'absolute_number': tryInt(get('absolute_number')),
            'identifiers': {
                'thetvdb': tryInt(episode['id'])
            },
            'type': 'episode',
            'titles': [get('episodename')] if get('episodename') else [],
            'images': {
                'poster': [poster] if poster else [],
            },
            'released': get('firstaired'),
            'plot': get('overview'),
            'firstaired': get('firstaired'),
            'language': get('language'),
        }

        if get('imdb_id'):
            episode_data['identifiers']['imdb'] = get('imdb_id')

        episode_data = dict((k, v) for k, v in episode_data.iteritems() if v)
        return episode_data

    def parseTime(self, time):
        return time

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            return True
        else:
            return False


config = [{
    'name': 'thetvdb',
    'groups': [
        {
            'tab': 'providers',
            'name': 'tmdb',
            'label': 'TheTVDB',
            'hidden': True,
            'description': 'Used for all calls to TheTVDB.',
            'options': [
                {
                    'name': 'api_key',
                    'default': '7966C02F860586D2',
                    'label': 'Api Key',
                },
            ],
        },
    ],
}]
