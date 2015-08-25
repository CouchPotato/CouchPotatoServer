import re

from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


autoload = 'TMDB'


class TMDB(UserscriptBase):

    version = 2

    includes = ['*://www.themoviedb.org/movie/*']

    def getMovie(self, url):
        match = re.search('(?P<id>\d+)', url)
        movie = fireEvent('movie.info_by_tmdb', identifier = match.group('id'), extended = False, merge = True)

        if movie['imdb']:
            return self.getInfo(movie['imdb'])

