import re
import traceback

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider
import six


log = CPLog(__name__)


class Base(TorrentMagnetProvider, RSS):

    urls = {
         'detail': 'https://torrentz2.eu/%s',
         'search': 'https://torrentz2.eu/feed?f=%s'
    }

    http_time_between_calls = 0

    def _searchOnTitle(self, title, media, quality, results):

        search_url = self.urls['search']

        # Create search parameters
        search_params = self.buildUrl(title, media, quality)

        min_seeds = tryInt(self.conf('minimal_seeds'))
        if min_seeds:
            search_params += ' seed > %s' % (min_seeds - 1)

        rss_data = self.getRSSData(search_url % search_params)

        if rss_data:
            try:

                for result in rss_data:

                    name = self.getTextElement(result, 'title')
                    detail_url = self.getTextElement(result, 'link')
                    description = self.getTextElement(result, 'description')

                    magnet = splitString(detail_url, '/')[-1]
                    magnet_url = 'magnet:?xt=urn:btih:%s&dn=%s&tr=%s' % (magnet.upper(), tryUrlencode(name), tryUrlencode('udp://tracker.openbittorrent.com/announce'))

                    reg = re.search('Size: (?P<size>\d+) (?P<unit>[KMG]B) Seeds: (?P<seeds>[\d,]+) Peers: (?P<peers>[\d,]+)', six.text_type(description))
                    size = reg.group('size')
                    unit = reg.group('unit')
                    seeds = reg.group('seeds').replace(',', '')
                    peers = reg.group('peers').replace(',', '')

                    multiplier = 1
                    if unit == 'GB':
                        multiplier = 1000
                    elif unit == 'KB':
                        multiplier = 0

                    results.append({
                        'id': magnet,
                        'name': six.text_type(name),
                        'url': magnet_url,
                        'detail_url': detail_url,
                        'size': tryInt(size)*multiplier,
                        'seeders': tryInt(seeds),
                        'leechers': tryInt(peers),
                    })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


config = [{
    'name': 'torrentz',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Torrentz',
            'description': 'Torrentz.eu was a free, fast and powerful meta-search engine combining results from dozens of search engines, Torrentz2.eu is trying to replace it. <a href="https://torrentz2.eu/" target="_blank">Torrentz2</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAQklEQVQ4y2NgAALjtJn/ycEMlGiGG0IVAxiwAKzOxaKGARcgxgC8YNSAwWoAzuRMjgsIugqfAUR5CZcBRIcHsWEAADSA96Ig020yAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True
                },
                {
                    'name': 'minimal_seeds',
                    'type': 'int',
                    'default': 1,
                    'advanced': True,
                    'description': 'Only return releases with minimal X seeds',
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
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]
