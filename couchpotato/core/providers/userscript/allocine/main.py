from bs4 import BeautifulSoup
from couchpotato.core.providers.userscript.base import UserscriptBase

class AlloCine(UserscriptBase):

    includes = ['http://www.allocine.fr/film/*']

    def getMovie(self, url):

        if not 'fichefilm_gen_cfilm' in url:
            return 'Url isn\'t from a movie'

        try:
            data = self.getUrl(url)
        except:
            return

        html = BeautifulSoup(data)
        title = html.find('title').contents[0].strip()
        split = title.split(') - ')

        name = split[0][:-5].strip()
        year = split[0][-4:]

        return self.search(name, year)
