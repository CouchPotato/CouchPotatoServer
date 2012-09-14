from couchpotato.core.logger import CPLog
from couchpotato.core.providers.userscript.base import UserscriptBase
import re
import traceback

log = CPLog(__name__)


class RottenTomatoes(UserscriptBase):

    includes = ['*://www.rottentomatoes.com/m/*/']
    excludes = ['*://www.rottentomatoes.com/m/*/*/']

    version = 2

    def getMovie(self, url):

        try:
            data = self.getUrl(url)
        except:
            return

        try:
            name = None
            year = None
            metas = re.findall("property=\"(video:release_date|og:title)\" content=\"([^\"]*)\"", data)

            for meta in metas:
                mname, mvalue = meta
                if mname == 'og:title':
                    name = mvalue.decode('unicode_escape')
                elif mname == 'video:release_date':
                    year = mvalue[:4]

            if name and year:
                return self.search(name, year)

        except:
            log.error('Failed parsing page for title and year: %s', traceback.format_exc())
