from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import re
import traceback

log = CPLog(__name__)


class AwesomeHD(TorrentProvider):

    urls = {
        'test': 'https://awesome-hd.net/',
        'detail': 'https://awesome-hd.net/torrents.php?torrentid=%s',
        'search': 'https://awesome-hd.net/searchapi.php?action=imdbsearch&passkey=%s&imdb=%s&internal=%s',
        'download': 'https://awesome-hd.net/torrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s',
    }
    http_time_between_calls = 1

    def _search(self, movie, quality, results):

        data = self.getHTMLData(self.urls['search'] % (self.conf('passkey'), movie['library']['identifier'], self.conf('only_internal')))

        if data:
            try:
                soup = BeautifulSoup(data)

                if soup.find('error'):
                    log.error(soup.find('error').get_text())
                    return

                authkey = soup.find('authkey').get_text()
                entries = soup.find_all('torrent')

                for entry in entries:

                    torrentscore = 0
                    torrent_id = entry.find('id').get_text()
                    name = entry.find('name').get_text()
                    year = entry.find('year').get_text()
                    releasegroup = entry.find('releasegroup').get_text()
                    resolution = entry.find('resolution').get_text()
                    encoding = entry.find('encoding').get_text()
                    freeleech = entry.find('freeleech').get_text()
                    torrent_desc = '/ %s / %s / %s ' % (releasegroup, resolution, encoding)

                    if freeleech == '0.25' and self.conf('prefer_internal'):
                        torrent_desc += '/ Internal'
                        torrentscore += 200

                    if encoding == 'x264' and self.conf('favor') in ['encode', 'both']:
                        torrentscore += 300
                    if re.search('Remux', encoding) and self.conf('favor') in ['remux', 'both']:
                        torrentscore += 200

                    results.append({
                        'id': torrent_id,
                        'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                        'url': self.urls['download'] % (torrent_id, authkey, self.conf('passkey')),
                        'detail_url': self.urls['detail'] % torrent_id,
                        'size': self.parseSize(entry.find('size').get_text()),
                        'seeders': tryInt(entry.find('seeders').get_text()),
                        'leechers': tryInt(entry.find('leechers').get_text()),
                        'score': torrentscore
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
