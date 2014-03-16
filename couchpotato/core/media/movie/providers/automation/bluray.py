from bs4 import BeautifulSoup
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation

log = CPLog(__name__)

autoload = 'Bluray'


class Bluray(Automation, RSS):

    interval = 1800
    rss_url = 'http://www.blu-ray.com/rss/newreleasesfeed.xml'
    backlog_url = 'http://www.blu-ray.com/movies/movies.php?show=newreleases&page=%s'

    def getIMDBids(self):

        movies = []

        if self.conf('backlog'):

            page = 0
            while True:
                page += 1

                url = self.backlog_url % page
                data = self.getHTMLData(url)
                soup = BeautifulSoup(data)

                try:
                    # Stop if the release year is before the minimal year
                    page_year = soup.body.find_all('center')[3].table.tr.find_all('td', recursive = False)[3].h3.get_text().split(', ')[1]
                    if tryInt(page_year) < self.getMinimal('year'):
                        break

                    for table in soup.body.find_all('center')[3].table.tr.find_all('td', recursive = False)[3].find_all('table')[1:20]:
                        name = table.h3.get_text().lower().split('blu-ray')[0].strip()
                        year = table.small.get_text().split('|')[1].strip()

                        if not name.find('/') == -1:  # make sure it is not a double movie release
                            continue

                        if tryInt(year) < self.getMinimal('year'):
                            continue

                        imdb = self.search(name, year)

                        if imdb:
                            if self.isMinimalMovie(imdb):
                                movies.append(imdb['imdb'])
                except:
                    log.debug('Error loading page: %s', page)
                    break

            self.conf('backlog', value = False)

        rss_movies = self.getRSSData(self.rss_url)

        for movie in rss_movies:
            name = self.getTextElement(movie, 'title').lower().split('blu-ray')[0].strip('(').rstrip()
            year = self.getTextElement(movie, 'description').split('|')[1].strip('(').strip()

            if not name.find('/') == -1: # make sure it is not a double movie release
                continue

            if tryInt(year) < self.getMinimal('year'):
                continue

            imdb = self.search(name, year)

            if imdb:
                if self.isMinimalMovie(imdb):
                    movies.append(imdb['imdb'])

        return movies


config = [{
    'name': 'bluray',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'bluray_automation',
            'label': 'Blu-ray.com',
            'description': 'Imports movies from blu-ray.com.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'backlog',
                    'advanced': True,
                    'description': 'Parses the history until the minimum movie year is reached. (Will be disabled once it has completed)',
                    'default': False,
                    'type': 'bool',
                },
            ],
        },
    ],
}]
