from couchpotato.core.event import fireEvent
from couchpotato.core.providers.userscript.base import UserscriptBase
import re


class TMDB(UserscriptBase):

    includes = ['http://www.themoviedb.org/movie/*']

    def getMovie(self, url):
        match = re.search('(?P<id>\d+)', url)
        movie = fireEvent('movie.info_by_tmdb', identifier = match.group('id'), extended = False, merge = True)

        if movie['imdb']:
            return self.getInfo(movie['imdb'])

