from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, getTitle, possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import re
import time

log = CPLog(__name__)


class NzbIndex(NZBProvider, RSS):

    urls = {
        'download': 'https://www.nzbindex.com/download/',
        'search': 'https://www.nzbindex.com/rss/?%s',
    }

    http_time_between_calls = 1 # Seconds

    def search(self, movie, quality):

        if self.isDisabled():
            return []

        results = ResultList(self, movie, quality)
        for title in possibleTitles(getTitle(movie['library'])):
            results.extend(self._search(title, movie, quality))

        return results

    def _search(self, title, movie, quality):

        results = []

        q = '"%s" %s %s' % (title, movie['library']['year'], quality.get('identifier'))
        arguments = tryUrlencode({
            'q': q,
            'age': Env.setting('retention', 'nzb'),
            'sort': 'agedesc',
            'minsize': quality.get('size_min'),
            'maxsize': quality.get('size_max'),
            'rating': 1,
            'max': 250,
            'more': 1,
            'complete': 1,
        })

        nzbs = self.getRSSData(self.urls['search'] % arguments)

        for nzb in nzbs:

            enclosure = self.getElement(nzb, 'enclosure').attrib
            nzbindex_id = int(self.getTextElement(nzb, "link").split('/')[4])

            try:
                description = self.getTextElement(nzb, "description")
            except:
                description = ''

            def extra_check(item):
                if '#c20000' in item['description'].lower():
                    log.info('Wrong: Seems to be passworded: %s', item['name'])
                    return False

                return True

            results.append({
                'id': nzbindex_id,
                'name': self.getTextElement(nzb, "title"),
                'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple()))),
                'size': tryInt(enclosure['length']) / 1024 / 1024,
                'url': enclosure['url'],
                'detail_url': enclosure['url'].replace('/download/', '/release/'),
                'description': description,
                'get_more_info': self.getMoreInfo,
                'extra_check': extra_check,
            })

        return results

    def getMoreInfo(self, item):
        try:
            if '/nfo/' in item['description'].lower():
                nfo_url = re.search('href=\"(?P<nfo>.+)\" ', item['description']).group('nfo')
                full_description = self.getCache('nzbindex.%s' % item['id'], url = nfo_url, cache_timeout = 25920000)
                html = BeautifulSoup(full_description)
                item['description'] = toUnicode(html.find('pre', attrs = {'id':'nfo0'}).text)
        except:
            pass

