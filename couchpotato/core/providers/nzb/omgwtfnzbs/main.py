from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, getTitle, possibleTitles
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.nzb.base import NZBProvider
from dateutil.parser import parse
from urlparse import urlparse, parse_qs
import time
import xml.etree.ElementTree as XMLTree

log = CPLog(__name__)


class OMGWTFNZBs(NZBProvider, RSS):

    urls = {
        'search': 'http://rss.omgwtfnzbs.com/rss-search.php?%s',
    }

    http_time_between_calls = 1 #seconds

    cat_ids = [
        ([15], ['dvdrip']),
        ([15, 16], ['brrip']),
        ([16], ['720p', '1080p', 'bd50']),
        ([17], ['dvdr']),
    ]
    cat_backup_id = 'movie'

    def search(self, movie, quality):

        pre_releases = fireEvent('quality.pre_releases', single = True)
        if self.isDisabled() or quality['identifier'] in pre_releases:
            return []

        results = ResultList(self, movie, quality)
        for title in possibleTitles(getTitle(movie['library'])):
            results.extend(self._search(title, movie, quality))

        return results

    def _search(self, title, movie, quality):
        results = []

        q = '%s %s' % (title, movie['library']['year'])
        params = tryUrlencode({
            'search': q,
            'catid': ','.join([str(x) for x in self.getCatId(quality['identifier'])]),
            'user': self.conf('username', default = ''),
            'api': self.conf('api_key', default = ''),
        })

        nzbs = self.getRSSData(self.urls['search'] % params)

        for nzb in nzbs:

            nzb_id = parse_qs(urlparse(self.getTextElement(nzb, 'link')).query).get('id')[0]
            enclosure = self.getElement(nzb, 'enclosure').attrib
            size = enclosure['length']

            results.append({
                'id': nzb_id,
                'name': toUnicode(self.getTextElement(nzb, 'title')),
                'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, 'pubDate')).timetuple()))),
                'size': tryInt(size) / 1024 / 1024,
                'url': enclosure['url'],
                'detail_url': self.getTextElement(nzb, 'link'),
                'description': self.getTextElement(nzb, 'description')
            })

        return results
