from urlparse import urlparse
import re
import traceback

from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString, tryInt, tryFloat
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.base import ResultList
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {}
    limits_reached = {}

    http_time_between_calls = 1  # Seconds

    def search(self, media, quality):
        hosts = self.getHosts()

        results = ResultList(self, media, quality, imdb_results = True)

        for host in hosts:
            if self.isDisabled(host):
                continue

            self._searchOnHost(host, media, quality, results)

        return results

    def _searchOnHost(self, host, media, quality, results):

        torrents = self.getJsonData(self.buildUrl(media, host), cache_timeout = 1800)

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

        host_list = []
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

            host_list.append({
                'use': uses[nr],
                'host': host,
                'name': name,
                'seed_ratio': tryFloat(ratio),
                'seed_time': tryInt(seed_time),
                'pass_key': key,
                'extra_score': tryInt(extra_score[nr]) if len(extra_score) > nr else 0
            })

        return host_list

    def belongsTo(self, url, provider = None, host = None):

        hosts = self.getHosts()

        for host in hosts:
            result = super(Base, self).belongsTo(url, host = host['host'], provider = provider)
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


config = [{
    'name': 'torrentpotato',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'TorrentPotato',
            'order': 10,
            'description': 'CouchPotato torrent provider. Checkout <a href="https://github.com/RuudBurger/CouchPotatoServer/wiki/CouchPotato-Torrent-Provider">the wiki page about this provider</a> for more info.',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAABnRSTlMAAAAAAABupgeRAAABSElEQVR4AZ2Nz0oCURTGv8t1YMpqUxt9ARFxoQ/gQtppgvUKcu/sxB5iBJkogspaBC6iVUplEC6kv+oiiKDNhAtt16roP0HQgdsMLgaxfvy4nHP4Pi48qE2g4v91JOqT1CH/UnA7w7icUlLawyEdj+ZI/7h6YluWbRiddHonHh9M70aj7VTKzuXuikUMci/EO/ACnAI15599oAk8AR/AgxBQNCzreD7bmpl+FOIVuAHqQDUcJo+AK+CZFKLt95/MpSmMt0TiW9POxse6UvYZ6zB2wFgjFiNpOGesR0rZ0PVPXf8KhUCl22CwClz4eN8weoZBb9c0bdPsOWvHx/cYu9Y0CoNoZTJrwAbn5DrnZc6XOV+igVbnsgo0IxEomlJuA1vUIYGyq3PZBChwmExCUSmVZgMBDIUCK4UCFIv5vHIhm/XUDeAf/ADbcpd5+aXSWQAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'use',
                    'default': ''
                },
                {
                    'name': 'host',
                    'default': '',
                    'description': 'The url path of your TorrentPotato provider.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': '0',
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'name',
                    'label': 'Username',
                    'default': '',
                },
                {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'default': '1',
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'default': '40',
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'pass_key',
                    'default': ',',
                    'label': 'Pass Key',
                    'description': 'Can be found on your profile page',
                    'type': 'combined',
                    'combine': ['use', 'host', 'pass_key', 'name', 'seed_ratio', 'seed_time', 'extra_score'],
                },
            ],
        },
    ],
}]
