from xml.etree.ElementTree import QName
import datetime
import re

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Rottentomatoes'


class Rottentomatoes(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        movies = []

        rotten_tomatoes_namespace = 'http://www.rottentomatoes.com/xmlns/rtmovie/'
        urls = dict(zip(splitString(self.conf('automation_urls')), [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]))

        for url in urls:

            if not urls[url]:
                continue

            rss_movies = self.getRSSData(url)
            rating_tag = str(QName(rotten_tomatoes_namespace, 'tomatometer_percent'))

            for movie in rss_movies:

                value = self.getTextElement(movie, "title")
                result = re.search('(?<=%\s).*', value)

                if result:

                    log.info2('Something smells...')
                    rating = tryInt(self.getTextElement(movie, rating_tag))
                    name = result.group(0)

                    if rating < tryInt(self.conf('tomatometer_percent')):
                        log.info2('%s seems to be rotten...', name)
                    else:

                        log.info2('Found %s fresh enough movies, enqueuing: %s', (rating, name))
                        year = datetime.datetime.now().strftime("%Y")
                        imdb = self.search(name, year)

                        if imdb and self.isMinimalMovie(imdb):
                            movies.append(imdb['imdb'])

        return movies


config = [{
    'name': 'rottentomatoes',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'rottentomatoes_automation',
            'label': 'Rottentomatoes',
            'description': 'Imports movies from rottentomatoes rss feeds specified below.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                    'default': '1',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                    'default': 'http://www.rottentomatoes.com/syndication/rss/in_theaters.xml',
                },
                {
                    'name': 'tomatometer_percent',
                    'default': '80',
                    'label': 'Tomatometer',
                    'description': 'Use as extra scoring requirement',
                },
            ],
        },
    ],
}]
