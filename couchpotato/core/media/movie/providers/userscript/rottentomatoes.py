import re
import traceback

from couchpotato import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


log = CPLog(__name__)

autoload = 'RottenTomatoes'


class RottenTomatoes(UserscriptBase):

    includes = ['*://www.rottentomatoes.com/m/*']
    excludes = ['*://www.rottentomatoes.com/m/*/*/']

    version = 3

    def getMovie(self, url):

        try:
            data = self.getUrl(url)
        except:
            return

        try:
            title = re.findall("<title>(.*)</title>", data)
            name_year = fireEvent('scanner.name_year', title[0].split(' - Rotten')[0].decode('unicode_escape'), single = True)
            name = name_year.get('name')
            year = name_year.get('year')

            if name and year:
                return self.search(name, year)

        except:
            log.error('Failed parsing page for title and year: %s', traceback.format_exc())
