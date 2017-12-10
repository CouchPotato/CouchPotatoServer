import re

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, splitString, removeEmpty
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Letterboxd'


class Letterboxd(Automation):

    url = 'http://letterboxd.com/%s/watchlist/page/%d/'
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

            soup = BeautifulSoup(self.getHTMLData(self.url % (username, 1)))

            pagination = soup.find_all('li', attrs={'class': 'paginate-page'})
            number_of_pages = tryInt(pagination[-1].find('a').get_text()) if pagination else 1
            pages = range(1, number_of_pages)

            for page in pages:
                soup = BeautifulSoup(self.getHTMLData(self.url % (username, page)))
                movies += self.getMoviesFromHTML(soup)

        return movies

    def getMoviesFromHTML(self, html):
        movies = []

        for movie in html.find_all('li', attrs={'class': 'poster-container'}):
            img = movie.find('img')
            title = img.get('alt')

            movies.append({
                'title': title
            })

        return movies

config = [{
    'name': 'letterboxd',
    'groups': [
        {
            'tab': 'automation',
            'list': 'watchlist_providers',
            'name': 'letterboxd_automation',
            'label': 'Letterboxd',
            'description': 'Import movies from any public <a href="http://letterboxd.com/" target="_blank">Letterboxd</a> watchlist',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                },
                {
                    'name': 'automation_urls',
                    'label': 'Username',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                },
            ],
        },
    ],
}]
