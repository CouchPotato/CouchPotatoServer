#########################################
####nCore CouchPotato TorrentProvider####
############# @by gala ##################
############# @updated by wroadd ########
############### 2017 ####################
#########################################
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import traceback
import json

log = CPLog(__name__)

class Base(TorrentProvider):
    urls = {
        'login': 'https://ncore.cc/login.php',
        'search': 'https://ncore.cc/torrents.php?kivalasztott_tipus=%s&mire=%s&miben=name&tipus=kivalasztottak_kozott&submit.x=0&submit.y=0&submit=Ok&tags=&searchedfrompotato=true&jsons=true'
    }

    http_time_between_calls = 1  # seconds

    def _searchOnTitle(self, title, movie, quality, results):
        hu_extra_score = 500 if self.conf('prefer_hu') else 0
        en_extra_score = 500 if self.conf('prefer_en') else 0

        self.doSearch(title, self.conf('hu_categories'), hu_extra_score, results)
        self.doSearch(title, self.conf('en_categories'), en_extra_score, results)

    def doSearch(self, title, categories, extra_score, results):
        url = self.urls['search'] % (categories, tryUrlencode(title))
        try:
            data = self.getJsonData(url)
            log.info('Number of torrents found on nCore = ' + str(data['total_results']))
            for d in data['results']:
                results.append({
                    'id': d['torrent_id'],
                    'leechers': d['leechers'],
                    'seeders': d['seeders'],
                    'name': toUnicode(d['release_name'].encode('ISO-8859-1')).strip(),
                    'url': d['download_url'],
                    'detail_url': d['details_url'],
                    'size': tryInt(d['size']) / (1024 * 1024),
                    'score': extra_score,
                })
        except:
            log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getLoginParams(self):
        return {
            'nev': str(self.conf('username')),
            'pass': str(self.conf('password')),
            'submitted': 1
        }

    def successLogin(self, output):
       return 'exit.php' in output.lower()

    loginCheckSuccess = successLogin

config = [{
              'name': 'ncore',
              'groups': [
                  {
                      'tab': 'searcher',
                      'list': 'torrent_providers',
                      'name': 'nCore',
                      'description': 'See <a href="https://ncore.cc/">nCore</a>',
                      'wizard': True,
                      'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABqUlEQVQ4jY3SPWsUYRTF8d86k7gbNb4loKxiEFKk0UJIo4KQQkgtduYLmEIrDVhZ2buxsLKyzQfwGwT7jY1IdEVxJbjG7OtkLfZOMiYWGXgYeObc/zn3zi0tUsEL3McFR3u+4g2eJ7O83OThFidLSEMxRIYB+uhiBz/Q4FSb26dJS4u0P1K+gmlMBGA3AFkB1MNvNONco5lmlM8jP+UD7oNCirG4P4HWyGcqFa4V/MFn/PwPIMG5KE4KreZvWUzmyeqq6/Pzh6fWaHi6suJTva4cLe4BsojYjw/brZbXtZovjcYo8uSkB0tLarWamwsLLkaqPUA+oG70/2Fjw7u1NVMBbWG6WvV4eVkndP0ioB+AXiQYhmgsRN1C5NzsUIJuQZgD2vZ3ICvMqpigdJfhd5wN8sTcnAy/6nWVEO4gq1Zdqla9X183Hne3csAmzuA4OuGSRHG+A+1wFpoO7iAdGv3/JBKINtqF4oH9jewV7iBN6W0zPsQ4Sv5d4ewAIF+sY6P6ZjLL5QE3tiJWtxAxH2zumjsnuDpq+1WKRzPsznAPU472fMNbPPsLszaznIb1BQAAAAAASUVORK5CYII=',
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
                              'default': 96,
                              'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                          },
                          {
                              'name': 'prefer_hu',
                              'label': 'Prefer Hungarian',
                              'type': 'bool',
                              'default': False,
                              'description': 'Favors Hungarian dubbed results.',
                          },
                          {
                              'name': 'prefer_en',
                              'label': 'Prefer English/Original',
                              'type': 'bool',
                              'default': False,
                              'description': 'Favors English or original language over Hungarian dubbed results.',
                          },
                          {
                              'name': 'hu_categories',
                              'advanced': True,
                              'default': 'xvid_hun,dvd_hun,dvd9_hun,hd_hun',
                              'description': 'Search categories for Hungarian dubbed movies',
                          },
                          {
                              'name': 'en_categories',
                              'advanced': True,
                              'default': 'xvid,dvd,dvd9,hd',
                              'description': 'Search categories for English or original language movies',
                          },
                          {
                              'name': 'extra_score',
                              'advanced': True,
                              'type': 'int',
                              'default': 0,
                              'description': 'Starting score for each release found via this provider.',
                          },
                      ],
                  },
              ],
          }]
