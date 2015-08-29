import traceback

from couchpotato.core.event import fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase


log = CPLog(__name__)

autoload = 'Flickchart'


class Flickchart(UserscriptBase):

    version = 2

    includes = ['http://www.flickchart.com/movie/*']

    def getMovie(self, url):

        try:
            data = self.getUrl(url)
        except:
            return

        try:
            start = data.find('<title>')
            end = data.find('</title>', start)
            page_title = data[start + len('<title>'):end].strip().split('- Flick')

            year_name = fireEvent('scanner.name_year', page_title[0], single = True)

            return self.search(year_name.get('name'), year_name.get('year'))
        except:
            log.error('Failed parsing page for title and year: %s', traceback.format_exc())

