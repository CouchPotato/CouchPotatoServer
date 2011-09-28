from beautifulsoup import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.userscript.base import UserscriptBase
import re


class IMDB(UserscriptBase):

    includes = ['http*://*.imdb.com/title/tt*', 'http*://imdb.com/title/tt*']

    def getMovie(self, url):

        data = self.urlopen(url)

        html = BeautifulSoup(data)
        headers = html.findAll('h5')

        # Don't add TV show
        for head in headers:
            if 'seasons' in head.lower():
                return 'IMDB url is a TV Show'

        identifier = re.search('(?P<id>tt[0-9{7}]+)', url).group('id')
        movie = fireEvent('movie.info', identifier = identifier, merge = True)

        return movie
