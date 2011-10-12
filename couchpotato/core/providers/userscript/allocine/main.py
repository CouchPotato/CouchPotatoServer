from beautifulsoup import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.userscript.base import UserscriptBase

class AlloCine(UserscriptBase):

    includes = ['http://www.allocine.fr/film/*']

    def getMovie(self, url):

        if not 'fichefilm_gen_cfilm' in url:
            return 'Url isn\'t from a movie'

        data = self.urlopen(url)

        html = BeautifulSoup(data)
        title = html.find('title').contents[0].strip()
        split = title.split(') - ')

        name = split[0][:-5].strip()
        year = split[0][-4:]

        result = self.search(name, year)
        if result:
            movie = fireEvent('movie.info', identifier = result.get('imdb'), merge = True)

            return movie
