from couchpotato.core.providers.userscript.base import UserscriptBase
import re


class Filmweb(UserscriptBase):

    includes = ['http://www.filmweb.pl/*']

    def getMovie(self, url):

        cookie = {'Cookie': 'welcomeScreen=welcome_screen'}

        try:
            data = self.urlopen(url, headers = cookie)
        except:
            return

        name = re.search("<h2.*?class=\"text-large caption\">(?P<name>[^<]+)</h2>", data)

        if name is None:
            name = re.search("<a.*?property=\"v:name\".*?>(?P<name>[^<]+)</a>", data)

        name = name.group('name').decode('string_escape')

        year = re.search("<span.*?id=filmYear.*?>\((?P<year>[^\)]+)\).*?</span>", data)
        year = year.group('year')

        return self.search(name, year)
