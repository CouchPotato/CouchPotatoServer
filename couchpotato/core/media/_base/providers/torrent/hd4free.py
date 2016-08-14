
import re
import json
import traceback

from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://hd4free.xyz/',
        'detail': 'https://hd4free.xyz/details.php?id=%s',
        'search': 'https://hd4free.xyz/searchapi.php?apikey=%s&username=%s&imdbid=%s&internal=%s',
        'download': 'https://hd4free.xyz/download.php?torrent=%s&torrent_pass=%s',
    }

    http_time_between_calls = 1  # Seconds
    login_fail_msg = 'Your apikey is not valid! Go to HD4Free and reset your apikey.'

    def _search(self, movie, quality, results):
        data = self.getJsonData(self.urls['search'] % (self.conf('apikey'), self.conf('username'), getIdentifier(movie), self.conf('internal_only')))

        if data:
            if 'error' in data:
                if self.login_fail_msg in data['error']: # Check for login failure
                    self.disableAccount()
                else:
                    log.error('%s returned an error (possible rate limit): %s', (self.getName(), data['error']))
                return

            try:
                #for result in data[]:
                for key, result in data.iteritems():
                    if tryInt(result['total_results']) == 0:
                        return
                    torrentscore = self.conf('extra_score')
                    releasegroup = result['releasegroup']
                    resolution = result['resolution']
                    encoding = result['encoding']
                    freeleech = tryInt(result['freeleech'])
                    seeders = tryInt(result['seeders'])
                    torrent_desc = '/ %s / %s / %s / %s seeders' % (releasegroup, resolution, encoding, seeders)

                    if freeleech > 0 and self.conf('prefer_internal'):
                        torrent_desc += '/ Internal'
                        torrentscore += 200

                    if seeders == 0:
                        torrentscore = 0

                    name = result['release_name']
                    year = tryInt(result['year'])

                    results.append({
                        'id': tryInt(result['torrentid']),
                        'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                        'url': self.urls['download'] % (result['torrentid'], result['torrentpass']),
                        'detail_url': self.urls['detail'] % result['torrentid'],
                        'size': tryInt(result['size']),
                        'seeders': tryInt(result['seeders']),
                        'leechers': tryInt(result['leechers']),
                        'age': tryInt(result['age']),
                        'score': torrentscore
                    })
            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
config = [{
    'name': 'hd4free',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'HD4Free',
            'wizard': True,
            'description': '<a href="https://hd4free.xyz" target="_blank">HD4Free</a>',
			'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMAAAAoLQ9TAAABX1BMVEUF6nsH33cJ03EJ1XIJ1nMKzXIKz28Lym4MxGsMxWsMx2wNvmgNv2kNwGkNwWwOuGgOuWYOuWcOumcOu2cOvmgPtWQPtmUPt2UPt2YQr2IQsGIQsGMQsmMQs2QRqmARq2ARrmERrmISpV4SpmASp14SqF8ToFsToFwToVwTo10TpV0UnFoUn1sVllcVmFgWkFUWklYXjVQXjlMXkFUYh1EYilIYi1MZhlEafk0af04agE4agU4beEobeUsbe0wcdUkeaUQebUYfZEMfZ0QgX0AgYEAgYUEhWj4iVz0iWD0jTzkkSzcmQTMmQzQnPTInPjInPzIoNy8oOC8oODAoOTAoOjApMi0pNC4pNS4qLCoqLSsqLisqMCwrJygrKCgrKCkrKSkrKikrKiorKyosIyYsIycsJCcsJScsJigtHyUuGCIuGiMuGyMuHCMuHCQvEyAvFSEvFiEvFyE0ABU0ABY5lYz4AAAA3ElEQVR4AWNIQAMMiYmJCYkIkMCQnpKWkZ4KBGlARlpaLEOor194kI+Pj6+PT0CET0AYg46Alr22NDeHkBinnq6SkitDrolDgYtaapajdpGppoFfGkMhv2GxE0uuPwNfsk6mhHMOQ54isxmbUJKCtWx+tIZQcDpDtqSol7qIMqsRu3dIhJxxFkOBoF2JG5O7lSqjh5S/tkkWQ5SBTbqnfkymv2WGLa95YCSDhZiMvKIwj4GJCpesuDivK0N6VFRUYlRyfHJUchQQJDMkxsfHJcTHAxEIxMVj+BZDAACjwkqhYgsTAAAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                    'description': 'Enter your site username.',
                },
                {
                    'name': 'apikey',
                    'default': '',
                    'label': 'API Key',
                    'description': 'Enter your site api key. This can be found on <a href="https://hd4free.xyz/usercp.php?action=security" target="_blank">Profile Security</a>',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 0,
                    'description': 'Will not be (re)moved until this seed ratio is met. HD4Free minimum is 1:1.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 0,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met. HD4Free minimum is 72 hours.',
                },
                {
                    'name': 'prefer_internal',
                    'advanced': True,
                    'type': 'bool',
                    'default': 1,
                    'description': 'Favors internal releases over non-internal releases.',
                },
                {
                    'name': 'internal_only',
                    'advanced': True,
                    'label': 'Internal Only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only download releases marked as HD4Free internal',
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
