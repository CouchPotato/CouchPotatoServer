import re

from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'CrowdAI'


class CrowdAI(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        movies = []

        urls = dict(zip(splitString(self.conf('automation_urls')), [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]))

        for url in urls:

            if not urls[url]:
                continue

            rss_movies = self.getRSSData(url)

            for movie in rss_movies:

                description = self.getTextElement(movie, 'description')
                grabs = 0

                for item in movie:
                    if item.attrib.get('name') == 'grabs':
                        grabs = item.attrib.get('value')
                        break

                if int(grabs) > tryInt(self.conf('number_grabs')):
                    title = re.match(r'.*Title: .a href.*/">(.*) \(\d{4}\).*', description).group(1)
                    log.info2('%s grabs for movie: %s, enqueue...', (grabs, title))
                    year = re.match(r'.*Year: (\d{4}).*', description).group(1)
                    imdb = self.search(title, year)

                    if imdb and self.isMinimalMovie(imdb):
                        movies.append(imdb['imdb'])

        return movies


config = [{
    'name': 'crowdai',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'crowdai_automation',
            'label': 'CrowdAI',
            'description': ('Imports from any newznab powered NZB providers RSS feed depending on the number of grabs per movie.',
                            'Go to your newznab site and find the RSS section. Then copy the copy paste the link under "Movies > x264 feed" here.'),
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
                    'default': 'http://YOUR_PROVIDER/rss?t=THE_MOVIE_CATEGORY&i=YOUR_USER_ID&r=YOUR_API_KEY&res=2&rls=2&num=100',
                },
                {
                    'name': 'number_grabs',
                    'default': '500',
                    'label': 'Grab threshold',
                    'description': 'Number of grabs required',
                },
            ],
        },
    ],
}]
