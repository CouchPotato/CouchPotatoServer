from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.show.base import ShowProvider
from thetvdb.tvdb_api import Tvdb 
import traceback

log = CPLog(__name__)


class TheTVDb(ShowProvider):
    
    def __init__(self):
        #addEvent('show.by_hash', self.byHash)
        addEvent('show.search', self.search, priority = 1)
        addEvent('show.info', self.getInfo, priority = 1)
        addEvent('show.episodes', self.getEpisodes, priority = 1)
        #addEvent('show.info_by_thetvdb', self.getInfoByTheTVDBId)

        # Use base wrapper
        #thetvdbtmdb.configure(self.conf('api_key'))
        self.tvdb = Tvdb(apikey="7966C02F860586D2", banners=True)

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

        if not results:
            log.debug('Searching for show: %s', q)

            raw = None
            try:
                raw = self.tvdb.search(search_string)
                
            except:  # XXX: Make more specific
                log.error('Failed searching TheTVDB for "%s": %s', (search_string, traceback.format_exc()))

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
                except SyntaxError, e:
                    log.error('Failed to parse XML response: %s', e)
                    return False

        return results

    def getEpisodes(self, identifier=None):
        if not identifier:
            return []
        
        try:
            show = self.tvdb[int(identifier)]
        except:
            return []
        
        result = []
        for season in show.values():
            for episode in season.values():
                # Consider cache
                result.append(self.parseEpisode(episode))
                
        return result
                
    def getInfo(self, identifier = None):
        cache_key = 'thetvdb.cache.%s' % identifier
        result = self.getCache(cache_key)

        if not result:
            result = {}
            show = None

            try:
                log.debug('Getting info: %s', cache_key)
                #show = thetvdb.imdbLookup(id = identifier)
                show = self.tvdb[int(identifier)]
            except:
                pass

            if show:
                #result = self.parseShow(show[0])
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
        
        ## Images
        poster = self.getImage(show, type = 'poster', size = 'cover')
        backdrop = self.getImage(show, type = 'fanart', size = 'w1280')
        #poster_original = self.getImage(show, type = 'poster', size = 'original')
        #backdrop_original = self.getImage(show, type = 'backdrop', size = 'original')
        
        ## Genres
        genres = [] if show['genre'] is None else show['genre'].strip('|').split('|')

        ##  Year (not really needed for show)
        year = None

        show_data = {
            'via_thetvdb': True,
            'thetvdb_id': int(show['id']),
            'titles': [show['seriesname'], ],
            'original_title': show['seriesname'],
            'images': {
                'poster': [poster] if poster else [],
                'backdrop': [backdrop] if backdrop else [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'imdb': show['imdb_id'],
            'runtime': show['runtime'],
            'released': show['firstaired'],
            'year': year,
            'plot': show['overview'],
            'genres': genres,
        }

        show_data = dict((k, v) for k, v in show_data.iteritems() if v)

        ## Add alternative names
        #for alt in ['original_name', 'alternative_name']:
            #alt_name = toUnicode(show.get(alt))
            #if alt_name and not alt_name in show_data['titles'] and alt_name.lower() != 'none' and alt_name != None:
                #show_data['titles'].append(alt_name)

        return show_data
    
    def parseEpisode(self, episode):
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
        poster = []
        backdrop = []
        
        ## Genres
        genres = []

        ##  Year (not really needed for episode)
        year = None

        episode_data = {
            'via_thetvdb': True,
            'thetvdb_id': int(episode['id']),
            'titles': [episode['episodename'], ],
            'original_title': episode['episodename'],
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
            'plot': episode['overview'],
            'genres': genres,
        }

        episode_data = dict((k, v) for k, v in episode_data.iteritems() if v)

        ## Add alternative names
        #for alt in ['original_name', 'alternative_name']:
            #alt_name = toUnicode(episode.get(alt))
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
