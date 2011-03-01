from __future__ import with_statement
from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import Provider
from couchpotato.environment import Env
from urllib import quote_plus
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
        return Env.setting(attr, 'TheMovieDB')

    def search(self, q, limit = 8, alternative = True):
        ''' Find movie by name '''

        if self.isDisabled():
            return False

        log.debug('TheMovieDB - Searching for movie: %s' % q)

        url = "%s/%s/%s/xml/%s/%s" % (self.apiUrl, 'Movie.search', 'en', self.conf('api_key'), quote_plus(self.toSearchString(q)))

        log.info('Searching: %s' % url)

        data = urllib2.urlopen(url)

        return self.parseXML(data, limit, alternative = alternative)

    def parseXML(self, data, limit, alternative = True):
        if data:
            log.debug('TheMovieDB - Parsing RSS')
            try:
                xml = self.getItems(data, 'movies/movie')

                results = []
                nr = 0
                for movie in xml:
                    id = int(self.gettextelement(movie, "id"))

                    name = self.gettextelement(movie, "name")
                    imdb = self.gettextelement(movie, "imdb_id")
                    year = str(self.gettextelement(movie, "released"))[:4]

                    # 1900 is the same as None
                    if year == '1900':
                        year = 'None'

                    results.append({
                        'id': id,
                        'name': self.toSaveString(name),
                        'imdb': imdb,
                        'year': year
                    })

                    alternativeName = self.gettextelement(movie, "alternative_name")
                    if alternativeName and alternative:
                        if alternativeName.lower() != name.lower() and alternativeName.lower() != 'none' and alternativeName != None:
                            results.append({
                                'id': id,
                                'name': self.toSaveString(alternativeName),
                                'imdb': imdb,
                                'year': year
                            })

                    nr += 1
                    if nr == limit:
                        break

                #log.info('TheMovieDB - Found: %s' % results)
                return results
            except SyntaxError:
                log.error('TheMovieDB - Failed to parse XML response from TheMovieDb')
                return False


    def isDisabled(self):
        if self.conf('api_key') == '':
            log.error('TheMovieDB - No API key provided for TheMovieDB')
            True
        else:
            False
