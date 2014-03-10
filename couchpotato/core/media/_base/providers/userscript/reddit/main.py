from couchpotato import fireEvent
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.providers.userscript.base import UserscriptBase


class Reddit(UserscriptBase):

    includes = ['*://www.reddit.com/r/Ijustwatched/comments/*']

    def getMovie(self, url):
        name = splitString(url, '/')[-1]
        if name.startswith('ijw_'):
            name = name[4:]

        year_name = fireEvent('scanner.name_year', name, single = True)

        return self.search(year_name.get('name'), year_name.get('year'))
