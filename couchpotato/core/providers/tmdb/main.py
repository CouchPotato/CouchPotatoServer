from __future__ import with_statement
from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString, toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
from couchpotato.environment import Env
from urllib import quote_plus
import copy
import simplejson as json
import urllib2

log = CPLog(__name__)

class TMDB(Provider):
    """Api for theMovieDb"""

    type = 'movie'
    apiUrl = 'http://api.themoviedb.org/2.1'
    imageUrl = 'http://hwcdn.themoviedb.org'

    def __init__(self):
        addEvent('provider.movie.search', self.search)

    def conf(self, attr):
        return Env.setting(attr, 'themoviedb')

    def search(self, q, limit = 12, alternative = True):
        ''' Find movie by name '''

        if self.isDisabled():
            return False

        log.debug('TheMovieDB - Searching for movie: %s' % q)

        url = "%s/%s/%s/json/%s/%s" % (self.apiUrl, 'Movie.search', 'en', self.conf('api_key'), quote_plus(simplifyString(q)))

        log.info('Searching: %s' % url)

        data = urllib2.urlopen(url)
        jsn = json.load(data)

        return self.parse(jsn, limit, alternative = alternative)

    def parse(self, data, limit, alternative = True):
        if data:
            log.debug('TheMovieDB - Parsing RSS')
            try:
                results = []
                nr = 0
                for movie in data:

                    year = str(movie['released'])[:4]

                    # Poster url
                    poster = ''
                    for p in movie['posters']:
                        p = p['image']
                        if(p['size'] == 'thumb'):
                            poster = p['url']
                            break

                    # 1900 is the same as None
                    if year == '1900' or year.lower() == 'none':
                        year = None

                    movie_data = {
                        'id': int(movie['id']),
                        'name': toUnicode(movie['name']),
                        'poster': poster,
                        'imdb': movie['imdb_id'],
                        'year': year,
                        'tagline': 'This is the tagline of the movie',
                    }
                    results.append(copy.deepcopy(movie_data))

                    alternativeName = movie['alternative_name']
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


    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('TheMovieDB - No API key provided for TheMovieDB')
            True
        else:
            False
