from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.base import ResultList
from couchpotato.core.providers.torrent.base import TorrentProvider
from couchpotato.environment import Env
import traceback

log = CPLog(__name__)

class Couchtarter(TorrentProvider):

    limits_reached = {}

    http_time_between_calls = 1 # Seconds

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
            'user': host['username'],
            'passkey': host['pass_key'],
            'imdbid': movie['library']['identifier'].replace('tt', '')
        })
        url = '%s&%s' % (host['host'], arguments)

        torrents = self.getJsonData(url, cache_timeout = 1800)

        if torrents:
            try:
                if torrents.get('Error'):
                    if 'Incorrect parameters.' in torrents['Error']:
                        log.error('Wrong parameters passed to: %s', host['host'])
                    elif 'Death by authorization.' in torrents['Error']:
                        log.error('Wrong username or pass key for: %s', host['host'])
                    else:
                        log.error('Unknown error for: %s', host['host'])
                    return #(can I disable this host somehow? and notify user?)

                elif torrents.get('Results'):
                    if 'None found' in torrents['Results']:
                        return
                    else:
                        for torrent in torrents['Results']:
                            print torrent['ReleaseName']
                            print torrent['Size']
                            print torrent['DownloadURL']
                            #results.append({
                            #    'id': tryInt(result.get('TorrentID')),
                            #    'name': toUnicode(result.get('ReleaseName')),
                            #    'url': result.get('DownloadURL'),
                            #    'detail_url': result.get('DetailURL'),
                            #    'size': tryInt(self.parseSize(result.get('Size'))),
                            #    'score': host['extra_score'],
                            #    'seeders': tryInt(result.get('Seeders'),
                            #    'leechers': tryInt(result.get('leechers'),
                            #    'resoultion': result.get('Resolution'),
                            #    'source': result.get('Media'),
                            #    'get_more_info': result.get('IMDbID')
                            #})

            except:
                log.error('Failed getting results from %s: %s', (host['host'], traceback.format_exc()))

    def getHosts(self):

        uses = splitString(str(self.conf('use')), clean = False)
        hosts = splitString(self.conf('host'), clean = False)
        usernames = splitString(self.conf('username'), clean = False)
        pass_keys = splitString(self.conf('pass_key'), clean = False)
        extra_score = splitString(self.conf('extra_score'), clean = False)

        list = []
        for nr in range(len(hosts)):

            try: key = pass_keys[nr]
            except: key = ''

            try: host = hosts[nr]
            except: host = ''

            list.append({
                'use': uses[nr],
                'host': host,
                'pass_key': key,
                'extra_score': tryInt(extra_score[nr]) if len(extra_score) > nr else 0
            })

        return list

    def belongsTo(self, url, provider = None, host = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Couchtater, self).belongsTo(url, host = host['host'], provider = provider)
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
