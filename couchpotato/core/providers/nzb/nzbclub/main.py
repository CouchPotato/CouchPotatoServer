from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import MovieProvider, SeasonProvider, EpisodeProvider
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time

log = CPLog(__name__)

class NZBClub(MultiProvider):

    def getTypes(self):
        return [Movie, Season, Episode]


class Base(NZBProvider, RSS):

    urls = {
        'search': 'http://www.nzbclub.com/nzbfeed.aspx?%s',
    }

    http_time_between_calls = 4 #seconds

    def _search(self, media, quality, results):

        nzbs = self.getRSSData(self.urls['search'] % self.buildUrl(media))

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

class Movie(MovieProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'q': '"%s"' % fireEvent('library.query', media['library'], single = True),
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return query

class Season(SeasonProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'q': fireEvent('library.query', media['library'], single = True),
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return query

class Episode(EpisodeProvider, Base):

    def buildUrl(self, media):
        query = tryUrlencode({
            'q': fireEvent('library.query', media['library'], single = True),
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        return query
