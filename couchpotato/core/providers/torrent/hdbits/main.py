from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider

import re
import json
import requests
import traceback

log = CPLog(__name__)


class HDBits(TorrentProvider):

    urls = {
        'test' : 'https://hdbits.org/',
        'detail' : 'https://hdbits.org/details.php?id=%s',
        'download' : 'https://hdbits.org/download.php?id=%s&passkey=%s',
        'api': 'https://hdbits.org/api/torrents'
    }

    status_codes = {
        1: 'Failure (something bad happened)',
        2: 'SSL Required - You should be on https://',
        3: 'JSON Malformed',
        4: 'Auth data missing',
        5: 'Auth failed'
    }

    http_time_between_calls = 1 #seconds

    def _post_query(self, **params):

        post_data = {
            'username': self.conf('username'),
            'passkey': self.conf('passkey')
        }
        post_data.update(params)

        req = requests.post(self.urls['api'],
            data=json.dumps(post_data))

        response = json.loads(req.text)

        if response['status'] != 0:
            log.error('Error searching hdbits: %s'
                % self.status_codes[response['status']])
        else:
            return response['data']

    def _search(self, movie, quality, results):

        match = re.match(r'tt(\d{7})',
            movie['library']['identifier'])

        data = self._post_query(imdb={'id': match.group(1)})

        if data:
            try:
                for result in data:
                    results.append({
                        'id': result['id'],
                        'name': result['name'],
                        'url': self.urls['download']
                            % (result['id'], self.conf('passkey')),
                        'detail_url': self.urls['detail'] % result['id'],
                        'size': self.parseSize(result['size']),
                        'seeders': tryInt(result['seeders']),
                        'leechers': tryInt(result['leechers'])
                    })
            except:
                log.error('Failed getting results from %s: %s',
                    (self.getName(), traceback.format_exc()))

