from bs4 import BeautifulSoup
from datetime import datetime
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import traceback
import re

log = CPLog(__name__)


class HDTorrents(TorrentProvider):

    urls = {
        'login' : 'https://www.hdts.ru/login.php',
        'detail' : 'https://www.hdts.ru/details.php?id=%s',
        'search' : 'https://www.hdts.ru/torrents.php?search=%s&active=1&options=%s',
        'home' : 'https://www.hdts.ru/%s',
    }

    cat_ids = [
        ([1], ['bd50']),
        ([2], ['1080p', '720p', 'brrip']),
        ([3], ['720p', 'brrip']),
        ([5], ['1080p', 'brrip']),
    ]

    http_time_between_calls = 1 #seconds

    def _search(self, movie, quality, results):

        cats = self.getCatId(quality['identifier'])
        if not cats:
            return

        url = self.urls['search'] % (movie['library']['identifier'], cats[0])
        data = self.getHTMLData(url, opener = self.login_opener)
        
        
        if data:
          
          # Remove HDTorrents NEW list
          split_data = data.partition('<!-- Show New Torrents After Last Visit -->\n\n\n\n')
          data = split_data[2]

          html = BeautifulSoup(data)
          try:
              #Get first entry in table
              entries = html.find_all('td', attrs={'align' : 'center'})
              torrent_id = entries[21].find('div')['id']
              torrent_age = datetime.now() - datetime.strptime(entries[15].get_text()[:8] + ' ' + entries[15].get_text()[-10::], '%H:%M:%S %d/%m/%Y')
              
              results.append({
                              'id': torrent_id,
                              'name': entries[28].find('a')['title'].strip('View details: '),
                              'url': self.urls['home'] % entries[13].find('a')['href'],
                              'detail_url': self.urls['detail'] % torrent_id,
                              'size': self.parseSize(entries[16].get_text()),
                              'age': torrent_age.days,
                              'seeders': tryInt(entries[18].get_text()),
                              'leechers': tryInt(entries[19].get_text()),
              })

              #Now attempt to get any others
              result_table = html.find('table', attrs = {'class' : 'mainblockcontenttt'})

              if not result_table:
                  return

              entries = result_table.find_all('td', attrs={'align' : 'center', 'class' : 'listas'})

              if not entries:
                  return

              for result in entries:
                  block2 = result.find_parent('tr').find_next_sibling('tr')
                  if not block2:
                      continue
                  cells = block2.find_all('td')
                  detail = cells[1].find('a')['href']
                  torrent_id = detail.replace('details.php?id=', '')
                  torrent_age = datetime.now() - datetime.strptime(cells[5].get_text(), '%H:%M:%S %d/%m/%Y')

                  results.append({
                                  'id': torrent_id,
                                  'name': cells[1].find('b').get_text().strip('\t '),
                                  'url': self.urls['home'] % cells[3].find('a')['href'],
                                  'detail_url': self.urls['home'] % cells[1].find('a')['href'],
                                  'size': self.parseSize(cells[6].get_text()),
                                  'age': torrent_age.days,
                                  'seeders': tryInt(cells[8].get_text()),
                                  'leechers': tryInt(cells[9].get_text()),
                  })

          except:
              log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return tryUrlencode({
            'uid': self.conf('username'),
            'pwd': self.conf('password'),
            'Login': 'submit',
        })

    def loginSuccess(self, output):
        return "if your browser doesn\'t have javascript enabled" or 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess
