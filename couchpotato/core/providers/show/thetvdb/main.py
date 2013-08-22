from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.show.base import ShowProvider
from tvdb_api import tvdb_api, tvdb_exceptions
from datetime import datetime
import traceback

log = CPLog(__name__)

# XXX: I return None in alot of functions when there is error or no value; check if I
#      should be returning an empty list or dictionary
# XXX: Consider grabbing zips to put less strain on tvdb
# XXX: Consider a cache; not implenented everywhere yet or at all
# XXX: Search by language; now ists defualt of "en"
# XXX: alternate titles do exist for show and episodes; add them
# XXX: Unicode stuff
# XXX: we have a getShow function but it it being used?
class TheTVDb(ShowProvider):

    def __init__(self):
        #addEvent('show.by_hash', self.byHash)
        addEvent('show.search', self.search, priority = 1)
        addEvent('show.info', self.getShowInfo, priority = 1)
        addEvent('season.info', self.getSeasonInfo, priority = 1)
        addEvent('episode.info', self.getEpisodeInfo, priority = 1)
        #addEvent('show.info_by_thetvdb', self.getInfoByTheTVDBId)

        # XXX: Load from somewhere else
        tvdb_api_parms = {
            'apikey':"7966C02F860586D2",
            'banners':True
            }

        self.tvdb = tvdb_api.Tvdb(**tvdb_api_parms)

    #def byHash(self, file):
        #''' Find show by hash '''

        #if self.isDisabled():
            #return False

        #cache_key = 'tmdb.cache.%s' % simplifyString(file)
        #results = self.getCache(cache_key)

        #if not results:
            #log.debug('Searching for show by hash: %s', file)
            #try:
                #raw = tmdb.searchByHashingFile(file)

                #results = []
                #if raw:
                    #try:
                        #results = self.parseShow(raw)
                        #log.info('Found: %s', results['titles'][0] + ' (' + str(results.get('year', 0)) + ')')

                        #self.setCache(cache_key, results)
                        #return results
                    #except SyntaxError, e:
                        #log.error('Failed to parse XML response: %s', e)
                        #return False
            #except:
                #log.debug('No shows known by hash for: %s', file)
                #pass

        #return results

    def search(self, q, limit = 12):
        ''' Find show by name
        show = {    'id': 74713,
                    'language': 'en',
                    'lid': 7,
                    'seriesid': '74713',
                    'seriesname': u'Breaking Bad',}
        '''

        if self.isDisabled():
            return False

        search_string = simplifyString(q)
        cache_key = 'thetvdb.cache.%s.%s' % (search_string, limit)
        results = self.getCache(cache_key)
        # TODO: cache is not returned

        if not results:
            log.debug('Searching for show: %s', q)

            raw = None
            try:
                raw = self.tvdb.search(search_string)
            except (tvdb_exceptions.tvdb_error, IOError), e:
                log.error('Failed searching TheTVDB for "%s": %s', (search_string, traceback.format_exc()))
                return None

            results = []
            if raw:
                try:
                    nr = 0

                    for show in raw:
                        show = self.tvdb[int(show['id'])]
                        results.append(self.parseShow(show))

                        nr += 1
                        if nr == limit:
                            break

                    log.info('Found: %s', [result['titles'][0] + ' (' + str(result.get('year', 0)) + ')' for result in results])

                    self.setCache(cache_key, results)
                    return results
                #except SyntaxError, e:
                #    log.error('Failed to parse XML response: %s', e)
                #    return False
                except (tvdb_exceptions.tvdb_error, IOError), e:
                    log.error('Failed parsing TheTVDB for "%s": %s', (show, traceback.format_exc()))
                    return False

        return results

    def getShow(self, identifier = None):
        show = None
        try:
            log.debug('Getting show: %s', identifier)
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed to getShowInfo for show id "%s": %s', (identifier, traceback.format_exc()))
            return None

        return show

    def getSeasonInfo(self, identifier=None, season_identifier=None):
        """Either return a list of all seasons or a single season by number.
        identifier is the show 'id'
        """
        if not identifier:
            return None

        # season_identifier must contain the 'show id : season number' since there is no tvdb id
        # for season and we need a reference to both the show id and season number
        if season_identifier:
            try: season_identifier = int(season_identifier.split(':')[1])
            except: return None

        cache_key = 'thetvdb.cache.%s.%s' % (identifier, season_identifier)
        log.debug('Getting SeasonInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed parsing TheTVDB SeasonInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
            return None

        result = []
        for number, season in show.items():
            if season_identifier is not None and number == season_identifier:
                result = self.parseSeason(show, (number, season))
                self.setCache(cache_key, result)
                return result
            else:
                result.append(self.parseSeason(show, (number, season)))

        self.setCache(cache_key, result)
        return result

    def getEpisodeInfo(self, identifier=None, season_identifier=None, episode_identifier=None):
        """Either return a list of all episodes or a single episode.
        If episode_identifer contains an episode number to search for
        """
        if not identifier and season_identifier is None:
            return None

        # season_identifier must contain the 'show id : season number' since there is no tvdb id
        # for season and we need a reference to both the show id and season number
        if season_identifier:
            try:
                identifier, season_identifier = season_identifier.split(':')
                season_identifier =  int(season_identifier)
            except: return None

        cache_key = 'thetvdb.cache.%s.%s.%s' % (identifier, episode_identifier, season_identifier)
        log.debug('Getting EpisodeInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        try:
            show = self.tvdb[int(identifier)]
        except (tvdb_exceptions.tvdb_error, IOError), e:
            log.error('Failed parsing TheTVDB EpisodeInfo for "%s" id "%s": %s', (show, identifier, traceback.format_exc()))
            return None

        result = []
        for number, season in show.items():
            if season_identifier is not None and number != season_identifier:
                continue

            for episode in season.values():
                if episode_identifier is not None and episode['id'] == toUnicode(episode_identifier):
                    result = self.parseEpisode(show, episode)
                    self.setCache(cache_key, result)
                    return result
                else:
                    result.append(self.parseEpisode(show, episode))

        self.setCache(cache_key, result)
        return result

    def getShowInfo(self, identifier = None):
        if not identifier:
            return None

        cache_key = 'thetvdb.cache.%s' % identifier
        log.debug('Getting showInfo: %s', cache_key)
        result = self.getCache(cache_key) or {}
        if result:
            return result

        show =  self.getShow(identifier=identifier)
        if show:
            result = self.parseShow(show)
            self.setCache(cache_key, result)

        return result

    #def getInfoByTheTVDBId(self, id = None):

        #cache_key = 'thetvdb.cache.%s' % id
        #result = self.getCache(cache_key)

        #if not result:
            #result = {}
            #show = None

            #try:
                #log.debug('Getting info: %s', cache_key)
                #show = tmdb.getShowInfo(id = id)
            #except:
                #pass

            #if show:
                #result = self.parseShow(show)
                #self.setCache(cache_key, result)

        #return result

    def parseShow(self, show):
        """
        show[74713] = {
                    'actors': u'|Bryan Cranston|Aaron Paul|Dean Norris|RJ Mitte|Betsy Brandt|Anna Gunn|Laura Fraser|Jesse Plemons|Christopher Cousins|Steven Michael Quezada|Jonathan Banks|Giancarlo Esposito|Bob Odenkirk|',
                    'added': None,
                    'addedby': None,
                    'airs_dayofweek': u'Sunday',
                    'airs_time': u'9:00 PM',
                    'banner': u'http://thetvdb.com/banners/graphical/81189-g13.jpg',
                    'contentrating': u'TV-MA',
                    'fanart': u'http://thetvdb.com/banners/fanart/original/81189-28.jpg',
                    'firstaired': u'2008-01-20',
                    'genre': u'|Crime|Drama|Suspense|',
                    'id': u'81189',
                    'imdb_id': u'tt0903747',
                    'language': u'en',
                    'lastupdated': u'1376620212',
                    'network': u'AMC',
                    'networkid': None,
                    'overview': u"Walter White, a struggling high school chemistry teacher is diagnosed with advanced lung cancer. He turns to a life of crime, producing and selling methamphetamine accompanied by a former student, Jesse Pinkman with the aim of securing his family's financial future before he dies.",
                    'poster': u'http://thetvdb.com/banners/posters/81189-22.jpg',
                    'rating': u'9.3',
                    'ratingcount': u'473',
                    'runtime': u'60',
                    'seriesid': u'74713',
                    'seriesname': u'Breaking Bad',
                    'status': u'Continuing',
                    'zap2it_id': u'SH01009396'}
        """

        # Make sure we have a valid show id, not '' or None
        #if len (show['id']) is 0:
        #    return None

        ## Images
        poster = self.getImage(show, type = 'poster', size = 'cover')
        backdrop = self.getImage(show, type = 'fanart', size = 'w1280')
        #poster_original = self.getImage(show, type = 'poster', size = 'original')
        #backdrop_original = self.getImage(show, type = 'backdrop', size = 'original')

        genres = [] if show['genre'] is None else show['genre'].strip('|').split('|')
        if show['firstaired'] is not None:
            try: year = datetime.strptime(show['firstaired'],  '%Y-%m-%d').year
            except: year =  None
        else:
            year = None

        show_data = {
            'id': int(show['id']),
            'type': 'show',
            'primary_provider': 'thetvdb',
            'titles': [show['seriesname'], ],
            'original_title': show['seriesname'],
            'images': {
                'poster': [poster] if poster else [],
                'backdrop': [backdrop] if backdrop else [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'year': year,
            'genres': genres,
            'imdb': show['imdb_id'],
            'zap2it_id': show['zap2it_id'],
            'seriesid': show['seriesid'],
            'network': show['network'],
            'networkid': show['networkid'],
            'airs_dayofweek': show['airs_dayofweek'],
            'airs_time': show['airs_time'],
            'firstaired': show['firstaired'],
            'released': show['firstaired'],
            'runtime': show['runtime'],
            'contentrating': show['contentrating'],
            'rating': show['rating'],
            'ratingcount': show['ratingcount'],
            'actors': show['actors'],
            'lastupdated': show['lastupdated'],
            'status': show['status'],
            'language': show['language'],
        }

        show_data = dict((k, v) for k, v in show_data.iteritems() if v)

        ## Add alternative names
        #for alt in ['original_name', 'alternative_name']:
            #alt_name = toUnicode(show['alt))
            #if alt_name and not alt_name in show_data['titles'] and alt_name.lower() != 'none' and alt_name != None:
                #show_data['titles'].append(alt_name)

        return show_data

    def parseSeason(self, show,  season_tuple):
        """
        contains no data
        """

        number, season = season_tuple
        title = toUnicode('%s - Season %s' % (show['seriesname'], str(number)))

        # XXX: work on title; added defualt_title to fix an error
        season_data = {
            'id': (show['id'] + ':' + str(number)),
            'type': 'season',
            'primary_provider': 'thetvdb',
            'titles': [title, ],
            'original_title': title,
            'via_thetvdb': True,
            'parent_identifier': show['id'],
            'seasonnumber': str(number),
            'images': {
                'poster': [],
                'backdrop': [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'year': None,
            'genres': None,
            'imdb': None,
        }

        season_data = dict((k, v) for k, v in season_data.iteritems() if v)
        return season_data

    def parseEpisode(self, show,  episode):
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

        ## Images
        #poster = self.getImage(episode, type = 'poster', size = 'cover')
        #backdrop = self.getImage(episode, type = 'fanart', size = 'w1280')
        ##poster_original = self.getImage(episode, type = 'poster', size = 'original')
        ##backdrop_original = self.getImage(episode, type = 'backdrop', size = 'original')

        poster = episode['filename'] or []
        backdrop = []
        genres = []
        plot = "%s - %sx%s - %s" %  (show['seriesname'],
                                     episode['seasonnumber'],
                                     episode['episodenumber'],
                                     episode['overview'])
        if episode['firstaired'] is not None:
            try: year = datetime.strptime(episode['firstaired'],  '%Y-%m-%d').year
            except: year =  None
        else:
            year = None

        episode_data = {
            'id': int(episode['id']),
            'type': 'episode',
            'primary_provider': 'thetvdb',
            'via_thetvdb': True,
            'thetvdb_id': int(episode['id']),
            'titles': [episode['episodename'], ],
            'original_title': episode['episodename'] ,
            'images': {
                'poster': [poster] if poster else [],
                'backdrop': [backdrop] if backdrop else [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'imdb': episode['imdb_id'],
            'runtime': None,
            'released': episode['firstaired'],
            'year': year,
            'plot': plot,
            'genres': genres,
            'parent_identifier': show['id'],
            'seasonnumber': episode['seasonnumber'],
            'episodenumber': episode['episodenumber'],
            'combined_episodenumber': episode['combined_episodenumber'],
            'absolute_number': episode['absolute_number'],
            'combined_season': episode['combined_season'],
            'productioncode': episode['productioncode'],
            'seriesid': episode['seriesid'],
            'seasonid': episode['seasonid'],
            'firstaired': episode['firstaired'],
            'thumb_added': episode['thumb_added'],
            'thumb_height': episode['thumb_height'],
            'thumb_width': episode['thumb_width'],
            'rating': episode['rating'],
            'ratingcount': episode['ratingcount'],
            'epimgflag': episode['epimgflag'],
            'dvd_episodenumber': episode['dvd_episodenumber'],
            'dvd_discid': episode['dvd_discid'],
            'dvd_chapter': episode['dvd_chapter'],
            'dvd_season': episode['dvd_season'],
            'tms_export': episode['tms_export'],
            'writer': episode['writer'],
            'director': episode['director'],
            'gueststars': episode['gueststars'],
            'lastupdated': episode['lastupdated'],
            'language': episode['language'],
        }

        episode_data = dict((k, v) for k, v in episode_data.iteritems() if v)

        ## Add alternative names
        #for alt in ['original_name', 'alternative_name']:
            #alt_name = toUnicode(episode['alt))
            #if alt_name and not alt_name in episode_data['titles'] and alt_name.lower() != 'none' and alt_name != None:
                #episode_data['titles'].append(alt_name)

        return episode_data

    def getImage(self, show, type = 'poster', size = 'cover'):
        """"""
        # XXX: Need to implement size
        image_url = ''

        for res, res_data in show['_banners'].get(type, {}).items():
            for bid, banner_info in res_data.items():
                image_url = banner_info.get('_bannerpath', '')
                break

        return image_url

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('No API key provided.')
            True
        else:
            False
