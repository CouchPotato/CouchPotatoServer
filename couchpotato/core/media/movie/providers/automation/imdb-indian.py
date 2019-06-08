from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt, splitString, removeEmpty
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation
from couchpotato import fireEvent


log = CPLog(__name__)

autoload = 'IMDBIndian'


class IMDBIndian(Automation):

    url = 'https://www.imdb.com/india/released/'

    interval = 1800

    def getIMDBids(self):

        log.info('IMDBIndian.getIMDBids called')
        
        # page = requests.get(url)
        # print(page)
        # soup = BeautifulSoup(page.text, 'html.parser')
        soup = BeautifulSoup(self.getHTMLData(self.url))

        items = soup.find_all('div', attrs={'class': 'trending-list-rank-item'})

        movies = []

        for item in items:
            # print(item)
            # print("---")
            containers = item.find_all('div', attrs={'class': 'trending-list-rank-item-data-container'})
            for container in containers:
                span = container.find('span', attrs={'class': 'trending-list-rank-item-name'})
                a = span.find('a')
                title_link = a.attrs['href']
                imdb_id = title_link.split('/')[2]
                
                info = fireEvent('movie.info', identifier = imdb_id, extended = False, merge = True)
                if self.isMinimalMovie(info):
                    movies.append(imdb_id)
        
        return movies

config = [{
    'name': 'imdbindian',
    'groups': [
        {
            'tab': 'automation',
            'list': 'automation_providers',
            'name': 'imdb_indian_automation',
            'label': 'IMDB Indian',
            'description': 'Import from <a href="https://www.imdb.com/india/released/" target="_blank">Trending Indian Movies</a>',
            'options': [
                {
                    'name': 'automation_enabled',
                    'default': False,
                    'type': 'enabler',
                }
            ],
        },
    ],
}]
