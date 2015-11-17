from couchpotato.core.helpers.variable import getImdb
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'MovieMeter'


class MovieMeter(UserscriptBase):

    includes = ['*://*.moviemeter.nl/film/*', '*://moviemeter.nl/film/*']

    version = 3

    def getMovie(self, url):

        cookie = {'Cookie': 'cok=1'}

        try:
            data = self.urlopen(url, headers = cookie)
        except:
            return

        return self.getInfo(getImdb(data))
