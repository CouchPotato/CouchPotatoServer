from urlparse import urlparse, parse_qs
import time

from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from dateutil.parser import parse


log = CPLog(__name__)


class Base(NZBProvider, RSS):

    urls = {
        'search': 'https://rss.omgwtfnzbs.org/rss-search.php?%s',
        'detail_url': 'https://omgwtfnzbs.org/details.php?id=%s',
    }

    http_time_between_calls = 1   # Seconds

    cat_ids = [
        ([15], ['dvdrip']),
        ([15, 16], ['brrip']),
        ([16], ['720p', '1080p', 'bd50']),
        ([17], ['dvdr']),
    ]
    cat_backup_id = 'movie'

    def search(self, movie, quality):

        if quality['identifier'] in fireEvent('quality.pre_releases', single = True):
            return []

        return super(Base, self).search(movie, quality)

    def _searchOnTitle(self, title, movie, quality, results):

        q = '%s %s' % (title, movie['info']['year'])
        params = tryUrlencode({
            'search': q,
            'catid': ','.join([str(x) for x in self.getCatId(quality)]),
            'user': self.conf('username', default = ''),
            'api': self.conf('api_key', default = ''),
        })

        nzbs = self.getRSSData(self.urls['search'] % params)

        for nzb in nzbs:

            enclosure = self.getElement(nzb, 'enclosure').attrib
            nzb_id = parse_qs(urlparse(self.getTextElement(nzb, 'link')).query).get('id')[0]

            results.append({
                'id': nzb_id,
                'name': toUnicode(self.getTextElement(nzb, 'title')),
                'age': self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, 'pubDate')).timetuple()))),
                'size': tryInt(enclosure['length']) / 1024 / 1024,
                'url': enclosure['url'],
                'detail_url': self.urls['detail_url'] % nzb_id,
                'description': self.getTextElement(nzb, 'description')
            })


config = [{
    'name': 'omgwtfnzbs',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'OMGWTFNZBs',
            'description': 'See <a href="http://omgwtfnzbs.org/">OMGWTFNZBs</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'api_key',
                    'label': 'Api Key',
                    'default': '',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'default': 20,
                    'type': 'int',
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
