import json
import traceback

from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider

log = CPLog(__name__)


# Norbits API details:
# Quality param:
# 720p=20, 1080p=19, SD=22

# Medium param:
# DVD=26, Blu-ray=27, Encode=29

# Codec param:
# x264=9,xvid=10

class Base(TorrentProvider):

  urls = {
    'test': 'https://norbits.net/',
    'detail': 'https://norbits.net/details.php?id=%s',
    'download': 'https://norbits.net/download.php?id=%s&passkey=%s',
    'api': 'https://norbits.net/api2.php?action=torrents'
  }
  http_time_between_calls = 1 # Seconds

  def getNorbitsQuality(self,quality):
    # Return the proper quality ID to use in the API, defaults to None which searchs for everything
    return {
      '1080p': 19,
      'brrip': 19,
      '720p': 20,
      'dvdrip': 22,
      'dvd': 22
    }.get(quality,None)

  def _post_query(self, search, quality=None):

    post_data = {
      'username': self.conf('username'),
      'passkey': self.conf('passkey'),
      'category': '1',
      'search': search
    }
    if quality:
      post_data.update({'quality': quality})

    try:
      result = self.getJsonData(self.urls['api'], data = json.dumps(post_data))
      if result:
        if int(result['status']) != 0:
          log.error('Error searching norbits: %s' % result['message'])
        else:
          return result['data']['torrents']
    except:
      pass
    return None

  def _searchOnTitle(self,title,media,quality,results):
    data = self._post_query(title,self.getNorbitsQuality(quality.get('custom').get('quality')))
    if data:
      try:
        for result in data:
          results.append({
            'id': result['id'],
            'name': result['name'],
            'url': self.urls['download'] % (result['id'], self.conf('passkey')),
            'detail_url': self.urls['detail'] % result['id'],
            'size': tryInt(int(result['size']) / 1024 / 1024)
            #'seeders': 1, # FIXME: this is currently missing in the API response
            #'leechers': 1, # FIXME: this is currently missing in the API response
          })
      except:
        log.error('Failed getting resutls from %s: %s' % (self.getName(), traceback.format_exc()))


config = [{
  'name': 'norbits',
  'groups': [
    {
      'tab': 'searcher',
      'list': 'torrent_providers',
      'name': 'Norbits',
      'description': '<a href="https://norbits.net">Norbits</a>',
      'wizard': True,
      'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAF/SURBVDhPY/j0+dv/yIKO/y6xFf/d4qv+uydU48UgNSC1ID0gvQwghkNUGVGaYRikFqQHpJfBKabiv31kKQZ2iikHK3aNq8IpD3IJg0ts5f/mKcv+1/QthOP6iYv/x5f0/LcOK/rvkVj9v2kypnxscdd/2/CS/wyVPfP/4wIxRV1gDbhALFCeobRjDpgTmNn0P6miH4j7/ofmtP7/8/fv/7U7jvwvaJmJJt//PyS7BSy2eP1ehAHaHun/HaPLwdjAJ+v/0xevIQY0zwDLS1pEgcVBWNYm9v+L1+/+r9x6EGGAgU82PJRNA/OACt6CDciHGvDo2av/z1+9A+MnL96AxRonLaHMgLr+RYQNwOWFl2/e/1+5hQQvoAcyCCxev+c/Q1XPAjAH3YDPX7/+37b/1H+YBdhAbHH3f4ZgYJS0TV8BTl0wAxyjy/6Xdc79n1Y1EZzi0BNSw8Ql/6OAyRickEDRhqwZ2RCQZtxJuQKSlCnLTJ3/GT59oSA7f/n6HwDsB57Xl/E1hQAAAABJRU5ErkJggg==',
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
              'name': 'passkey',
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
              'default': 40,
              'description': 'Will not be (re)moved until this seed time (in hours) is met.',
          },
          {
              'name': 'extra_score',
              'advanced': True,
              'label': 'Extra score',
              'type': 'int',
              'default': 20,
              'description': 'Starting score for each release found via this provider',
          }
      ],
    },
  ],
}]
