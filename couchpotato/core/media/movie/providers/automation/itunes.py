from xml.etree.ElementTree import QName
import datetime
import traceback
import xml.etree.ElementTree as XMLTree

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'ITunes'


class ITunes(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        movies = []

        enablers = [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]
        urls = splitString(self.conf('automation_urls'))

        namespace = 'http://www.w3.org/2005/Atom'
        namespace_im = 'http://itunes.apple.com/rss'

        index = -1
        for url in urls:

            index += 1
            if len(enablers) == 0 or len(enablers) < index or not enablers[index]:
                continue

            try:
                cache_key = 'itunes.rss.%s' % md5(url)
                rss_data = self.getCache(cache_key, url)

                data = XMLTree.fromstring(rss_data)

                if data is not None:
                    entry_tag = str(QName(namespace, 'entry'))
                    rss_movies = self.getElements(data, entry_tag)

                    for movie in rss_movies:
                        name_tag = str(QName(namespace_im, 'name'))
                        name = self.getTextElement(movie, name_tag)

                        releaseDate_tag = str(QName(namespace_im, 'releaseDate'))
                        releaseDateText = self.getTextElement(movie, releaseDate_tag)
                        year = datetime.datetime.strptime(releaseDateText, '%Y-%m-%dT00:00:00-07:00').strftime("%Y")

                        imdb = self.search(name, year)

                        if imdb and self.isMinimalMovie(imdb):
                            movies.append(imdb['imdb'])

            except:
                log.error('Failed loading iTunes rss feed: %s %s', (url, traceback.format_exc()))

        return movies


config = [{
    'name': 'itunes',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'itunes_automation',
            'label': 'iTunes',
            'description': 'From any <a href="http://itunes.apple.com/rss" target="_blank">iTunes</a> Store feed. Url should be the RSS link.',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                },
                {
                    'name': 'automation_urls_use',
                    'label': 'Use',
                    'default': ',',
                },
                {
                    'name': 'automation_urls',
                    'label': 'url',
                    'type': 'combined',
                    'combine': ['automation_urls_use', 'automation_urls'],
                    'default': 'https://itunes.apple.com/rss/topmovies/limit=25/xml,',
                },
            ],
        },
    ],
}]
