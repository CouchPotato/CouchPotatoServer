from couchpotato.core.logger import CPLog
from couchpotato.core.providers.userscript.base import UserscriptBase
import traceback

log = CPLog(__name__)


class AlloCine(UserscriptBase):

    includes = ['http://www.allocine.fr/film/*']

    def getMovie(self, url):

        if not 'fichefilm_gen_cfilm' in url:
            return 'Url isn\'t from a movie'

        try:
            data = self.getUrl(url)
        except:
            return

        name = None
        year = None

        try:
            start = data.find('<title>')
            end = data.find('</title>', start)
            page_title = data[start + len('<title>'):end].strip().split('-')

            name = page_title[0].strip()
            year = page_title[1].strip()[-4:]
            return self.search(name, year)
        except:
            log.error('Failed parsing page for title and year: %s', traceback.format_exc())

