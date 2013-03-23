from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from bs4 import BeautifulSoup
import re

log = CPLog(__name__)


class Letterboxd(Automation):
    url = 'http://letterboxd.com/%s/watchlist/'
    pattern = re.compile(r'(.*)\((\d*)\)')

    def getIMDBids(self):

        if not self.conf('automation_username'):
            log.error('Please fill in your username')
            return []

        movies = []

        for movie in self.getWatchlist():
            imdb_id = self.search(movie.get('title'), movie.get('year'), imdb_only = True)
            movies.append(imdb_id)

        return movies

    def getWatchlist(self):
        url = self.url % self.conf('automation_username')
        soup = BeautifulSoup(self.getHTMLData(url))

        movies = []

        for movie in soup.find_all('a', attrs = { 'class': 'frame' }):
            match = filter(None, self.pattern.split(movie['title']))
            movies.append({ 'title': match[0], 'year': match[1] })

        return movies
