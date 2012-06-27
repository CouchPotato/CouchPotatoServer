from BeautifulSoup import BeautifulSoup
from couchpotato.core.providers.userscript.base import UserscriptBase


class Filmstarts(UserscriptBase):

    includes = ['*://www.filmstarts.de/kritiken/*']

    def getMovie(self, url):
        try:
            data = self.getUrl(url)
        except:
            return

        html = BeautifulSoup(data)

        table = html.find("table", attrs={"class": "table_02 fs11"})
        name = table.find("tr", text="Originaltitel").parent.parent.td.text
        year = table.find("tr", text="Produktionsjahr").parent.parent.td.text

        return self.search(name, year)
