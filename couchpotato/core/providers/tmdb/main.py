from __future__ import with_statement
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
from couchpotato.environment import Env
from libs.themoviedb import tmdb
from urllib import quote_plus
import copy
import simplejson as json
import urllib2

log = CPLog(__name__)

class TMDBWrapper(Provider):
    """Api for theMovieDb"""

    type = 'movie'
    apiUrl = 'http://api.themoviedb.org/2.1'
    imageUrl = 'http://hwcdn.themoviedb.org'

    def __init__(self):
        addEvent('provider.movie.search', self.search)
        addEvent('provider.movie.info', self.getInfo)

        # Use base wrapper
        tmdb.Config.api_key = self.conf('api_key')

    def conf(self, attr):
        return Env.setting(attr, 'themoviedb')

    def search(self, q, limit = 12, alternative = True):
        ''' Find movie by name '''

        if self.isDisabled():
            return False

        log.debug('TheMovieDB - Searching for movie: %s' % q)

        raw = tmdb.search(simplifyString(q))

        #url = "%s/%s/%s/json/%s/%s" % (self.apiUrl, 'Movie.search', 'en', self.conf('api_key'), quote_plus(simplifyString(q)))


#        data = urllib2.urlopen(url)
#        jsn = json.load(data)

        if raw:
            log.debug('TheMovieDB - Parsing RSS')
            try:
                results = []
                nr = 0
                for movie in raw:

                    for k, x in movie.iteritems():
                        print k
                        print x

                    year = str(movie.get('released', 'none'))[:4]

                    # Poster url
                    poster = ''
                    for p in movie.get('images'):
                        if(p.get('type') == 'poster'):
                            poster = p.get('thumb')
                            break

                    # 1900 is the same as None
                    if year == '1900' or year.lower() == 'none':
                        year = None

                    movie_data = {
                        'id': int(movie.get('id', 0)),
                        'name': toUnicode(movie.get('name')),
                        'poster': poster,
                        'imdb': movie.get('imdb_id'),
                        'year': year,
                        'tagline': 'This is the tagline of the movie',
                    }
                    results.append(copy.deepcopy(movie_data))

                    alternativeName = movie.get('alternative_name')
                    if alternativeName and alternative:
                        if alternativeName.lower() != movie['name'].lower() and alternativeName.lower() != 'none' and alternativeName != None:
                            movie_data['name'] = toUnicode(alternativeName)
                            results.append(copy.deepcopy(movie_data))
                    nr += 1
                    if nr == limit:
                        break

                log.info('TheMovieDB - Found: %s' % [result['name'] + u' (' + str(result['year']) + ')' for result in results])
                return results
            except SyntaxError, e:
                log.error('TheMovieDB - Failed to parse XML response from TheMovieDb: %s' % e)
                return False

        return results

    def getInfo(self):
        pass

    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('TheMovieDB - No API key provided for TheMovieDB')
            True
        else:
            False
