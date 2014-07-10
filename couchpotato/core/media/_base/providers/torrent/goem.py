import re
from bs4 import BeautifulSoup
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog

__author__ = 'Scott Faria - scott.faria@gmail.com'

log = CPLog(__name__)


class Base(TorrentProvider):

    http_time_between_calls = 1

    urls = {
        'test': 'http://goem.org/',
        'base_url': 'http://goem.org',
        'login': 'http://goem.org/takelogin.php',
        'login_check': 'http://goem.org/my.php',
        'search': 'http://goem.org/advanced.php?action=search&imdb=%s&title=&title-tag=%s&title-tag-type=any&year=%d&page=%d',
    }

    source = '&source%%5B%%5D=%s'

    def _find_quality_params(self, quality_id):
        quality_id = quality_id.upper()
        if quality_id == 'HD':
            return {'tag': '1080P;720P', 'param': False}
        elif quality_id == 'SD':
            return {'tag': '-1080P;-720P', 'param': False}
        elif quality_id == '1080P':
            return {'tag': '1080P', 'param': False}
        elif quality_id == '720P':
            return {'tag': '720P', 'param': False}
        elif quality_id in ['DVDR', 'DVDRIP']:
            return {'tag': 'DVD', 'param': True}
        elif quality_id in ['BRDISK', 'BRRIP']:
            return {'tag': 'BluRay', 'param': True}
        elif quality_id in ['SCREENER', 'R5', 'TELECINE', 'TELESYNC', 'CAM']:
            return None  # Not allowed to be uploaded to goem
        else:
            return None

    def _get_page_count(self, html):
        nav_div = html.find('p', attrs={'class', 'pager'})
        if nav_div:
            page_links = nav_div.find_all('a')
            if page_links:
                pages = [0]
                for link in page_links:
                    matcher = re.search('page=(\d*)', link['href'])
                    pages.append(tryInt(matcher.group(0)))
                return max(pages)
        return 1

    def _add_torrent(self, table_row, results):
        torrent_tds = table_row.find_all('td')
        if len(torrent_tds) == 11:
            url_base = self.urls['base_url']
            torrent_id = torrent_tds[0].find('a')['href'].replace('/details.php?id=', '')
            download_url = url_base + torrent_tds[1].find('a')['href']
            details_link = torrent_tds[5].find('a')
            details_url = url_base + details_link['href']
            torrent_name = details_link.string
            torrent_seeders = tryInt(re.sub('[^0-9]', '', unicode(torrent_tds[7].find('nobr').contents[0].string)))
            torrent_leechers = tryInt(re.sub('[^0-9]', '', unicode(torrent_tds[7].find('nobr').contents[2].string)))
            torrent_size = self.parseSize(torrent_tds[9].find('span').string)

            results.append({
                'id': torrent_id,
                'name': torrent_name,
                'url': download_url,
                'detail_url': details_url,
                'size': torrent_size,
                'seeders': torrent_seeders,
                'leechers': torrent_leechers,
            })

    def _format_url(self, current_page, imdb_id, year, quality_tag, use_source_tag):
        if use_source_tag:
            return self.urls['search'] % (imdb_id, "", year, current_page) + self.source % quality_tag
        else:
            return self.urls['search'] % (imdb_id, quality_tag, year, current_page)

    # noinspection PyBroadException
    def _search(self, movie, quality, results):
        quality_map = self._find_quality_params(quality['identifier'])
        if quality_map is None:
            return

        quality = quality_map['tag']
        use_source_tag = quality_map['param']

        year = movie['library']['year']
        imdb_id = movie['library']['identifier']

        current_page = 1
        pages = -1

        while True:
            try:
                url = self._format_url(current_page, imdb_id, year, quality, use_source_tag)
                data = self.getHTMLData(url, opener=self.login_opener)

                if data:
                    html = BeautifulSoup(data)
                    if pages == -1:
                        pages = self._get_page_count(html)

                    torrent_table = html.find('table', attrs={'id': 'browse'})
                    if torrent_table:
                        torrent_rows = torrent_table.find_all('tr', attrs={'class': 'table_row'})
                        for row in torrent_rows:
                            self._add_torrent(row, results)

                    if current_page >= pages:
                        break
            except:
                log.error('Unexpected error while searching %s: %s', (self.getName(), traceback.format_exc()))
                return

    def getLoginParams(self):
        return tryUrlencode({
            'goeser': self.conf('username'),
            'gassmord': self.conf('password'),
            'login': 'submit',
        })

    def loginSuccess(self, output):
        return 'Login failed!' not in output.lower()

    def isEnabled(self):
        return super(Base, self).isEnabled() and self.getDomain()


config = [{
              'name': 'goem',
              'groups': [
                  {
                      'tab': 'searcher',
                      'list': 'torrent_providers',
                      'name': 'Goem',
                      'description': 'See <a href="http://www.goem.org">Goem</a>',
                      'icon': 'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAA AAAAAAD///8A////AOrp6BXm5uQZ////AP///wD///8A////AP///wD///8A////AP///wD///8A ////AP///wD///8A/Pz8AdTW0V6SfmHwl4px/////wD///8A////AP///wD///8A////AP///wD/ //8A////AP///wD///8A////AODd1iibgFn/0quC/59+Xv/Z3Ngm1tXOPqGZiud9dWH9cmpX/YSA c/25uLFi9PT2Cv///wD///8A////AP///wD08/IMsZ12//bruv/Epnv/c2dO/3ZpSf2QhGP93M+q +v3yxvj36r34xrmP+pOIb/3ExL1k////AP///wD///8A////AMe+s2qok3b/nXdc/2hRN/3WzrL4 +vLQ9c3FuvWYhmv47OS89f7+1/X+/tH3xLeQ+r68svf///8A////AP///wD///8Ap4xq/cqrff3L uaP4/v7y88zBqvX1+f5il496uZuNcff068rwt6eW98Kzj/jEt5XQ2NnWKP///wD///8A////AIx6 YP2sm3z6/v788/7++e3Sx7Pub2BG931fPfiaiG/ztauS8Nvd3F6Lfl6269+5+KyjkfX6+voD//// APDw8A6il3X9rJ6K+vLr2/OQgGf30siz7cq/q+qllX3u/vni48Cylu5jVj7ucGRE6eXbu/fHup36 7OvqFP///wDp6OYYsqWD/c7Ct/i5oYP3g2VLyYRmRuX38eLg/v763f7+9t3+/vXjtaeQ8LWtk/X+ /vL149m6+t7e2Kv///8A9PT0Cryvjv3TysD3nIx5+H5gRO1bQiL65NvL5ff0495yYXSj6+TQcP7+ 7umtn433r6KG+O/lyvrc2dTn////AP///wDAtZv90caz+P7+/vOmlnz3oJOF8/7+/uP+/vnZgHB2 ofPu3+nKv6vzr66jkYx7XK3Pwar66enkGf///wD///8AzcO4Tca6nfj+/v71/v7+8LSfjvWNe2b3 9/Tu6f7+/un+/v7q7Oba8F9TPPWDclX10cSz/fb29gf///8A////APz9/AHEtp3908m7+vv4+fWW b0r6qZNnu416Z+DZ0cfzbVI7+qyehOr++/L3/Pbr+tTPxf3///8A////AP///wD///8A7OnoFb2t kv3m39f6jH9t/VpFKf21opH4q5+M+JiRgKiThmat/v77+sm+sP38/P4B////AP///wD///8A//// AP///wD29vYHw7Wj/cGxof3t5+L6/v7++Pj39fihlIT9va+e/dbMw/36+/wD////AP///wD///8A ////AP///wD///8A////AP///wDy8O4P2dPL/dnTy/3d19D94NjR/fDt7BL///8A////AP///wD/ //8A//8AAM//AACMPwAAgA8AAMADAADBAwAAwBEAAMABAADAAAAAwCAAAMABAADgAQAA4AEAAPAD AAD4BwAA/h8AAA==',
                      'wizard': True,
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
                              'name': 'password',
                              'default': '',
                              'type': 'password',
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


