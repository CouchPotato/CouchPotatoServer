from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time

log = CPLog(__name__)


class NZBClub(NZBProvider, RSS):

    urls = {
        'search': 'https://www.nzbclub.com/nzbfeeds.aspx?%s',
    }

    http_time_between_calls = 4  #seconds

    def _searchOnTitle(self, title, movie, quality, results):

        q = '"%s %s"' % (title, movie['library']['year'])

        q_param = tryUrlencode({
            'q': q,
        })

        params = tryUrlencode({
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })

        nzbs = self.getRSSData(self.urls['search'] % ('%s&%s' % (q_param, params)))

        for nzb in nzbs:

            nzbclub_id = tryInt(self.getTextElement(nzb, "link").split('/nzb_view/')[1].split('/')[0])
            enclosure = self.getElement(nzb, "enclosure").attrib
            size = enclosure['length']
            date = self.getTextElement(nzb, "pubDate")

            def extra_check(item):
                full_description = self.getCache('nzbclub.%s' % nzbclub_id, item['detail_url'], cache_timeout = 25920000)

                for ignored in ['ARCHIVE inside ARCHIVE', 'Incomplete', 'repair impossible']:
                    if ignored in full_description:
                        log.info('Wrong: Seems to be passworded or corrupted files: %s', item['name'])
                        return False

                return True

            results.append({
                'id': nzbclub_id,
                'name': toUnicode(self.getTextElement(nzb, "title")),
                'age': self.calculateAge(int(time.mktime(parse(date).timetuple()))),
                'size': tryInt(size) / 1024 / 1024,
                'url': enclosure['url'].replace(' ', '_'),
                'detail_url': self.getTextElement(nzb, "link"),
                'get_more_info': self.getMoreInfo,
                'extra_check': extra_check
            })

    def getMoreInfo(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('pre', attrs = {'class':'nfo'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item

    def extraCheck(self, item):
        full_description = self.getCache('nzbclub.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)

        if 'ARCHIVE inside ARCHIVE' in full_description:
            log.info('Wrong: Seems to be passworded files: %s', item['name'])
            return False

        return True
