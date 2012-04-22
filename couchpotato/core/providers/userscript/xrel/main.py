from BeautifulSoup import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getImdb
from couchpotato.core.providers.userscript.base import UserscriptBase


class XRel(UserscriptBase):

    includes = ['*://www.xrel.to/movie/*']

    def getMovie(self, url):
        try:
            data = self.getUrl(url)
        except:
            return

        html = BeautifulSoup(data)
        imdb_url = html.find(text="IMDb.com").parent["title"]
        return fireEvent("movie.info", identifier = getImdb(imdb_url), merge = True)
