from bs4 import BeautifulSoup
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt, possibleTitles, getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urlparse import urlparse, parse_qs
import re
import traceback

log = CPLog(__name__)


class DownRev(TorrentProvider, RSS):

    urls = {
        'test' : 'https://www.downrev.net/',
        'login' : 'https://www.downrev.net/takelogin.php',
        'detail' : 'https://www.downrev.net/torrent/%s',
        'search' : 'https://www.downrev.net/rss2.php?cats=%d&type=dl&passkey=%s&like=%s',
        'download' : 'https://www.downrev.net/down.php?id=%s&passkey=%s',
        'login_check': 'http://www.downrev.net/inbox',
    }

    cat_ids = [
        ([68], ['1080p']),
        ([45], ['720p']),
        ([36], ['dvdrip', 'scr', 'r5']),
        ([65], ['brrip']),
        ([34], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):

        url = self.urls['search'] % (self.getCatId(quality['identifier'])[0], self.conf('passkey') , possibleTitles(getTitle(movie['library']))[0].replace(' ', '.'))
        data = self.getRSSData(url, opener = self.login_opener)

        if data:
            try:
                for result in data:
                    title = self.getTextElement(result, "title")
                    desc = self.getTextElement(result, "description")
                    link = self.getTextElement(result, "link")

                    # Extract from link
                    o = urlparse(link)
                    ID = parse_qs(o.query)['id'][0]

                    p = re.compile(r'\W*Size[^: ]*:\s*(\d+.\d+\s\w+)\D*Leechers[^: ]*:\s(\d+)\D*Seeders[^: ]*:\s(\d+)')
                    m2 = p.findall(desc.replace('/', '').replace('<br/>', ''))

                    size = m2[0][0]
                    leechers = m2[0][1]
                    seeders = m2[0][2]

                    results.append({
                        'id': ID,
                        'name': title,
                        'url': self.urls['download'] % (ID, self.conf('passkey')),
                        'detail_url': self.urls['detail'] % ID,
                        'size': self.parseSize(size),
                        'seeders': tryInt(seeders),
                        'leechers': tryInt(leechers)
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

