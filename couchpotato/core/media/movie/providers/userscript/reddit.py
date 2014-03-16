from couchpotato import fireEvent
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Reddit'


class Reddit(UserscriptBase):

    includes = ['*://www.reddit.com/r/Ijustwatched/comments/*']

    def getMovie(self, url):
        name = splitString(splitString(url, '/ijw_')[-1], '/')[0]

        if name.startswith('ijw_'):
            name = name[4:]

        year_name = fireEvent('scanner.name_year', name, single = True)

        return self.search(year_name.get('name'), year_name.get('year'))
