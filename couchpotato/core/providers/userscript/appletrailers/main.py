from couchpotato.core.event import fireEvent
from couchpotato.core.providers.userscript.base import UserscriptBase
import re


class AppleTrailers(UserscriptBase):

    includes = ['http://trailers.apple.com/trailers/*']

    def getMovie(self, url):

        data = self.urlopen(url)

        name = re.search('(?P<id>(var trailerTitle(.+);))', data)
        name = name.group('id').split(' = \'')[1].strip()[:-2].decode('string_escape')

        date = re.search('(?P<id>(var releaseDate(.+);))', data)
        year = date.group('id').split(' = \'')[1].strip()[:-2]

        result = self.search(name, year)
        if result:
            movie = fireEvent('movie.info', identifier = result.get('imdb'), merge = True)

            return movie
