from bs4 import BeautifulSoup
from couchpotato import fireEvent

from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Filmweb'


class Filmweb(UserscriptBase):

    version = 3

    includes = ['http://www.filmweb.pl/film/*']

    def getMovie(self, url):

        cookie = {'Cookie': 'welcomeScreen=welcome_screen'}

        try:
            data = self.urlopen(url, headers = cookie)
        except:
            return

        html = BeautifulSoup(data)
        name = html.find('meta', {'name': 'title'})['content'][:-9].strip()
        name_year = fireEvent('scanner.name_year', name, single = True)
        name = name_year.get('name')
        year = name_year.get('year')

        return self.search(name, year)
