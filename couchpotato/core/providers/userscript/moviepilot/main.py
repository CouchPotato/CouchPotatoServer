from BeautifulSoup import BeautifulSoup
from couchpotato.core.providers.userscript.base import UserscriptBase


class Moviepilot(UserscriptBase):

    includes = ['*://www.moviepilot.de/movies/*']

    def getMovie(self, url):
        try:
            data = self.getUrl(url)
        except:
            return

        html = BeautifulSoup(data)
        temp = html.find("div", attrs={"itemscope": "itemscope"}).h2.span.text
        name, year = temp.split("(")
        name = name.strip()
        year = year.split(")")[0].strip()

        return self.search(name, year)
