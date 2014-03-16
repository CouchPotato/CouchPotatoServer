import re

from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


autoload = 'AppleTrailers'


class AppleTrailers(UserscriptBase):

    includes = ['http://trailers.apple.com/trailers/*']

    def getMovie(self, url):

        try:
            data = self.getUrl(url)
        except:
            return

        name = re.search("trailerTitle.*=.*\'(?P<name>.*)\';", data)
        name = name.group('name').decode('string_escape')

        date = re.search("releaseDate.*=.*\'(?P<date>.*)\';", data)
        year = date.group('date')[:4]

        return self.search(name, year)
