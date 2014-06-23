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
         'detail': 'https://torrentz.eu/%s',
         'search': 'https://torrentz.eu/feed?q=%s',
         'verified_search': 'https://torrentz.eu/feed_verified?q=%s'
    }

    http_time_between_calls = 0

    def _search(self, media, quality, results):

        search_url = self.urls['verified_search'] if self.conf('verified_only') else self.urls['search']

        # Create search parameters
        search_params = self.buildUrl(media)

        smin = quality.get('size_min')
        smax = quality.get('size_max')
        if smin and smax:
            search_params += ' size %sm - %sm' % (smin, smax)

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

                    reg = re.search('Size: (?P<size>\d+) MB Seeds: (?P<seeds>[\d,]+) Peers: (?P<peers>[\d,]+)', six.text_type(description))
                    size = reg.group('size')
                    seeds = reg.group('seeds').replace(',', '')
                    peers = reg.group('peers').replace(',', '')

                    results.append({
                        'id': magnet,
                        'name': six.text_type(name),
                        'url': magnet_url,
                        'detail_url': detail_url,
                        'size': tryInt(size),
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
            'description': 'Torrentz is a free, fast and powerful meta-search engine. <a href="https://torrentz.eu/">Torrentz</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAQklEQVQ4y2NgAALjtJn/ycEMlGiGG0IVAxiwAKzOxaKGARcgxgC8YNSAwWoAzuRMjgsIugqfAUR5CZcBRIcHsWEAADSA96Ig020yAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': True
                },
                {
                    'name': 'verified_only',
                    'type': 'bool',
                    'default': True,
                    'advanced': True,
                    'description': 'Only search verified releases',
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
