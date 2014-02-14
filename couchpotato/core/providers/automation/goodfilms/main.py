from bs4 import BeautifulSoup
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation

log = CPLog(__name__)


class Goodfilms(Automation):

    url = 'http://goodfil.ms/%s/queue?page=%d&without_layout=1'

    interval = 1800

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

        movies = []
        page = 1

        while True:
            url = self.url % (self.conf('automation_username'), page)
            data = self.getHTMLData(url)
            soup = BeautifulSoup(data)

            this_watch_list = soup.find_all('div', attrs = {
                'class': 'movie',
                'data-film-title': True
            })

            if not this_watch_list:  # No Movies
                break

            for movie in this_watch_list:
                movies.append({ 'title': movie['data-film-title'], 'year': movie['data-film-year'] })

            if not 'next page' in data.lower():
                break

            page += 1

        return movies
