from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toSafeString
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class IPTorrents(TorrentProvider):

    urls = {
        'test' : 'http://www.iptorrents.com/',
        'base_url' : 'http://www.iptorrents.com',
        'login' : 'http://www.iptorrents.com/torrents/',
        'login_check': 'http://www.iptorrents.com/inbox.php',
        'search' : 'http://www.iptorrents.com/torrents/?l%d=1%s&q=%s&qf=ti&p=%d',
    }

    cat_ids = [
        ([48], ['720p', '1080p', 'bd50']),
        ([72], ['cam', 'ts', 'tc', 'r5', 'scr']),
        ([7], ['dvdrip', 'brrip']),
        ([6], ['dvdr']),
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        freeleech = '' if not self.conf('freeleech') else '&free=on'

        pages = 1
        current_page = 1
        while current_page <= pages and not self.shuttingDown():

            url = self.urls['search'] % (self.getCatId(quality['identifier'])[0], freeleech, tryUrlencode('%s %s' % (title.replace(':', ''), movie['library']['year'])), current_page)
            data = self.getHTMLData(url)

            if data:
                html = BeautifulSoup(data)

                try:
                    page_nav = html.find('span', attrs = {'class' : 'page_nav'})
                    if page_nav:
                        next_link = page_nav.find("a", text = "Next")
                        if next_link:
                            final_page_link = next_link.previous_sibling.previous_sibling
                            pages = int(final_page_link.string)

                    result_table = html.find('table', attrs = {'class' : 'torrents'})

                    if not result_table or 'nothing found!' in data.lower():
                        return

                    entries = result_table.find_all('tr')

                    columns = self.getColumns(entries)

                    if 'seeders' not in columns or 'leechers' not in columns:
                        log.warning('Unrecognized table format returned')
                        return

                    for result in entries[1:]:

                        cells = result.find_all('td')
                        if len(cells) <= 1:
                            break

                        torrent = cells[1].find('a')

                        torrent_id = torrent['href'].replace('/details.php?id=', '')
                        torrent_name = torrent.string
                        torrent_download_url = self.urls['base_url'] + (result.find_all('td')[3].find('a'))['href'].replace(' ', '.')
                        torrent_details_url = self.urls['base_url'] + torrent['href']
                        torrent_size = self.parseSize(result.find_all('td')[5].string)
                        torrent_seeders = tryInt(cells[columns['seeders']].string)
                        torrent_leechers = tryInt(cells[columns['leechers']].string)

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

    def getColumns(self, entries):
        result = {}

        for x, col in enumerate(entries[0].find_all('th')):
            key = toSafeString(col.text).strip().lower()

            if not key:
                continue

            result[key] = x

        return result

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        }

    def loginSuccess(self, output):
        return 'don\'t have an account' not in output.lower()

    def loginCheckSuccess(self, output):
        return '/logout.php' in output.lower()
