from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, splitString, removeEmpty
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import re

log = CPLog(__name__)


class Letterboxd(Automation):

    url = 'http://letterboxd.com/%s/watchlist/'
    pattern = re.compile(r'(.*)\((\d*)\)')

    interval = 1800

    def getIMDBids(self):

        urls = splitString(self.conf('automation_urls'))

        if len(urls) == 0:
            return []

        movies = []

        for movie in self.getWatchlist():
            imdb_id = self.search(movie.get('title'), movie.get('year'), imdb_only = True)
            movies.append(imdb_id)

        return movies

    def getWatchlist(self):

        enablers = [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]
        urls = splitString(self.conf('automation_urls'))

        index = -1
        movies = []
        for username in urls:

            index += 1
            if not enablers[index]:
                continue

            soup = BeautifulSoup(self.getHTMLData(self.url % username))

            for movie in soup.find_all('a', attrs = {'class': 'frame'}):
                match = removeEmpty(self.pattern.split(movie['title']))
                movies.append({'title': match[0], 'year': match[1] })

        return movies
