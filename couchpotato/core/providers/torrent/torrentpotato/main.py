from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.torrent.base import TorrentProvider
from urlparse import urlparse
import re
import traceback

log = CPLog(__name__)


class TorrentPotato(TorrentProvider):

    urls = {}
    limits_reached = {}

    http_time_between_calls = 1  # Seconds

    def search(self, movie, quality):
        hosts = self.getHosts()

        results = ResultList(self, movie, quality, imdb_results = True)

        for host in hosts:
            if self.isDisabled(host):
                continue

            self._searchOnHost(host, movie, quality, results)

        return results

    def _searchOnHost(self, host, movie, quality, results):

        arguments = tryUrlencode({
            'user': host['name'],
            'passkey': host['pass_key'],
            'imdbid': movie['library']['identifier']
        })
        url = '%s?%s' % (host['host'], arguments)

        torrents = self.getJsonData(url, cache_timeout = 1800)

        if torrents:
            try:
                if torrents.get('error'):
                    log.error('%s: %s', (torrents.get('error'), host['host']))
                elif torrents.get('results'):
                    for torrent in torrents.get('results', []):
                        results.append({
                            'id': torrent.get('torrent_id'),
                            'protocol': 'torrent' if re.match('^(http|https|ftp)://.*$', torrent.get('download_url')) else 'torrent_magnet',
                            'provider_extra': urlparse(host['host']).hostname or host['host'],
                            'name': toUnicode(torrent.get('release_name')),
                            'url': torrent.get('download_url'),
                            'detail_url': torrent.get('details_url'),
                            'size': torrent.get('size'),
                            'score': host['extra_score'],
                            'seeders': torrent.get('seeders'),
                            'leechers': torrent.get('leechers'),
                            'seed_ratio': host['seed_ratio'],
                            'seed_time': host['seed_time'],
                        })

            except:
                log.error('Failed getting results from %s: %s', (host['host'], traceback.format_exc()))

    def getHosts(self):

        uses = splitString(str(self.conf('use')), clean = False)
        hosts = splitString(self.conf('host'), clean = False)
        names = splitString(self.conf('name'), clean = False)
        seed_times = splitString(self.conf('seed_time'), clean = False)
        seed_ratios = splitString(self.conf('seed_ratio'), clean = False)
        pass_keys = splitString(self.conf('pass_key'), clean = False)
        extra_score = splitString(self.conf('extra_score'), clean = False)

        list = []
        for nr in range(len(hosts)):

            try: key = pass_keys[nr]
            except: key = ''

            try: host = hosts[nr]
            except: host = ''

            try: name = names[nr]
            except: name = ''

            try: ratio = seed_ratios[nr]
            except: ratio = ''

            try: seed_time = seed_times[nr]
            except: seed_time = ''

            list.append({
                'use': uses[nr],
                'host': host,
                'name': name,
                'seed_ratio': tryFloat(ratio),
                'seed_time': tryInt(seed_time),
                'pass_key': key,
                'extra_score': tryInt(extra_score[nr]) if len(extra_score) > nr else 0
            })

        return list

    def belongsTo(self, url, provider = None, host = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(TorrentPotato, self).belongsTo(url, host = host['host'], provider = provider)
            if result:
                return result

    def isDisabled(self, host = None):
        return not self.isEnabled(host)

    def isEnabled(self, host = None):

    # Return true if at least one is enabled and no host is given
        if host is None:
            for host in self.getHosts():
                if self.isEnabled(host):
                    return True
            return False

        return TorrentProvider.isEnabled(self) and host['host'] and host['pass_key'] and int(host['use'])
