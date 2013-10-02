from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import MultiProvider
from couchpotato.core.providers.info.base import MovieProvider, ShowProvider
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)


class IPTorrents(MultiProvider):

    def getTypes(self):
        return [Movie, Show]


class Base(TorrentProvider):

    urls = {
        'test' : 'http://www.iptorrents.com/',
        'base_url' : 'http://www.iptorrents.com',
        'login' : 'http://www.iptorrents.com/torrents/',
        'login_check': 'http://www.iptorrents.com/inbox.php',
        'search' : 'http://www.iptorrents.com/torrents/?%s%%s&q=%s&qf=ti&p=%%d',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _buildUrl(self, query, quality_identifier, cat_ids_group = None):

        cat_ids = self.getCatId(quality_identifier, cat_ids_group)

        if not len(cat_ids):
            log.warning('Unable to find category for quality %s', quality_identifier)
            return

        return self.urls['search'] % ("&".join(("l%d=" % x) for x in cat_ids), tryUrlencode(query).replace('%', '%%'))

    def _searchOnTitle(self, title, media, quality, results):

        freeleech = '' if not self.conf('freeleech') else '&free=on'

        base_url = self.buildUrl(title, media, quality)
        if not base_url: return

        pages = 1
        current_page = 1
        while current_page <= pages and not self.shuttingDown():
            data = self.getHTMLData(
                base_url  % (freeleech, current_page),
                opener = self.login_opener
            )

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

                    for result in entries[1:]:

                        torrent = result.find_all('td')
                        if len(torrent) <= 1:
                            break

                        torrent = torrent[1].find('a')

                        torrent_id = torrent['href'].replace('/details.php?id=', '')
                        torrent_name = torrent.string
                        torrent_download_url = self.urls['base_url'] + (result.find_all('td')[3].find('a'))['href'].replace(' ', '.')
                        torrent_details_url = self.urls['base_url'] + torrent['href']
                        torrent_size = self.parseSize(result.find_all('td')[5].string)
                        torrent_seeders = tryInt(result.find('td', attrs = {'class' : 'ac t_seeders'}).string)
                        torrent_leechers = tryInt(result.find('td', attrs = {'class' : 'ac t_leechers'}).string)

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

    def getLoginParams(self):
        return tryUrlencode({
            'username': self.conf('username'),
            'password': self.conf('password'),
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return 'don\'t have an account' not in output.lower()

    def loginCheckSuccess(self, output):
        return '/logout.php' in output.lower()


class Movie(MovieProvider, Base):

    cat_ids = [
        ([48], ['720p', '1080p', 'bd50']),
        ([72], ['cam', 'ts', 'tc', 'r5', 'scr']),
        ([7], ['dvdrip', 'brrip']),
        ([6], ['dvdr']),
    ]

    def buildUrl(self, title, media, quality):
        query = '%s %s' % (title.replace(':', ''), media['library']['year'])

        return self._buildUrl(query, quality['identifier'])


class Show(ShowProvider, Base):

    cat_ids = [
        ('season', [
            ([65], ['hdtv_sd', 'hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ]),
        ('episode', [
            ([5], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
            ([4, 78, 79], ['hdtv_sd'])
        ])
    ]

    def buildUrl(self, title, media, quality):
        if media['type'] not in ['season', 'episode']:
            return

        return self._buildUrl(title.replace(':', ''), quality['identifier'], media['type'])