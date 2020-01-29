import traceback

from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import six


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://iptorrents.com/',
        'base_url': 'https://iptorrents.com',
        'search': 'https://iptorrents.com/t?%s%%s&q=%s&qf=ti#torrents&p=%%d',
    }

    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'Invalid username and cookie combination'
    cat_backup_id = None


    def buildUrl(self, title, media, quality):
        return self._buildUrl(title.replace(':', ''), quality)

    def _buildUrl(self, query, quality):

        cat_ids = self.getCatId(quality)

        if not cat_ids:
            log.warning('Unable to find category ids for identifier "%s"', quality.get('identifier'))
            return None

        query = query.replace('"', '')

        return self.urls['search'] % ("&".join(("%d=" % x) for x in cat_ids), tryUrlencode(query).replace('%', '%%'))

    def _searchOnTitle(self, title, media, quality, results):

        freeleech = '' if not self.conf('freeleech') else '&free=on'

        base_url = self.buildUrl(title, media, quality)
        if not base_url: return

        pages = 1
        current_page = 1
        while current_page <= pages and not self.shuttingDown():
            data = self.getHTMLData(base_url % (freeleech, current_page), headers = self.getRequestHeaders())
            
            if data:
                html = BeautifulSoup(data)

                try:
                    page_nav = html.find('span', attrs = {'class': 'page_nav'})
                    if page_nav:
                        next_link = page_nav.find("a", text = "Next")
                        if next_link:
                            final_page_link = next_link.previous_sibling.previous_sibling
                            pages = int(final_page_link.string)

                    result_table = html.find('table', id="torrents")
                    
                    if not result_table or 'nothing found!' in data.lower():
                        return

                    entries = result_table.find_all('tr')

                    for result in entries[1:]:

                        torrent = result.find_all('td')
                        if len(torrent) <= 1:
                            break

                        torrent = torrent[1].find('a')

                        torrent_id = torrent['href'].replace('/details.php?id=', '')
                        torrent_name = six.text_type(torrent.string)
                        torrent_download_url = self.urls['base_url'] + (result.find_all('td')[3].find('a'))['href'].replace(' ', '.')
                        torrent_details_url = self.urls['base_url'] + torrent['href']
                        torrent_size = self.parseSize(result.find_all('td')[5].string)
                        torrent_seeders = tryInt(result.find('td', attrs = {'class': 'ac t_seeders'}).string)
                        torrent_leechers = tryInt(result.find('td', attrs = {'class': 'ac t_leechers'}).string)

                        results.append({
                            'id': torrent_id,
                            'name': torrent_name,
                            'url': torrent_download_url,
                            'detail_url': torrent_details_url,
                            'size': torrent_size,
                            'seeders': torrent_seeders,
                            'leechers': torrent_leechers,
                        })

                except:
                    log.error('Failed to parsing %s: %s', (self.getName(), traceback.format_exc()))
                    break

            current_page += 1

    def getRequestHeaders(self):
        return {
            'Cookie': self.conf('cookiesetting') or ''
        }
    
    def download(self, url = '', nzb_id = ''):
        try:
            return self.urlopen(url, headers=self.getRequestHeaders())
        except:
            log.error('Failed getting release from %s: %s', (self.getName(), traceback.format_exc()))

        return 'try_next'


config = [{
    'name': 'iptorrents',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'IPTorrents',
            'description': '<a href="https://iptorrents.com" target="_blank">IPTorrents</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABRklEQVR42qWQO0vDUBiG8zeKY3EqQUtNO7g0J6ZJ1+ifKIIFQXAqDYKCyaaYxM3udrZLHdRFhXrZ6liCW6mubfk874EESgqaeOCF7/Y8hEh41aq6yZi2nyZgBGya9XKtZs4No05pAkZV2YbEmyMMsoSxLQeC46wCTdPPY4HruPQyGIhF97qLWsS78Miydn4XdK46NJ9OsQAYBzMIMf8MQ9wtCnTdWCaIDx/u7uljOIQEe0hiIWPamSTLay3+RxOCSPI9+RJAo7Er9r2bnqjBFAqyK+VyK4f5/Cr5ni8OFKVCz49PFI5GdNvvU7ttE1M1zMU+8AMqFksEhrMnQsBDzqmDAwzx2ehRLwT7yyCI+vSC99c3mozH1NxrJgWWtR1BOECfEJSVCm6WCzJGCA7+IWhBsM4zywDPwEp4vCjx2DzBH2ODAfsDb33Ps6dQwJgAAAAASUVORK5CYII=',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'freeleech',
                    'default': 0,
                    'type': 'bool',
                    'description': 'Only search for [FreeLeech] torrents.',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
				{
                    'name': 'cookiesetting',
                    'label': 'Cookies',
                    'default': 'uid=1234;pass=567845439634987',
                    'description': 'Use DevTools or Firebug to get these values after logging in on your browser',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]

