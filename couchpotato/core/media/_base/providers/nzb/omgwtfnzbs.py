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
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQEAIAAADAAbR1AAADbElEQVR4AZ2UW0ybZRiAy/OvdHaLYvB0YTRIFi7GkM44zRLmIfNixkWdiRMyYoxRE8/TC7MYvXCGEBmr3mxLwVMwY0wYA7e6Wso4lB6h/U9taSlMGIfBXLYlJMyo0S///2dJI5lxN8/F2/f9nu9737e/jYmXr6KTbN9BGG9HE/NotQ76UWziNzrXFiETk/5ARUNH+7+0kW7fSgTl0VKGOLZzidOkmuuIo7q2oTArNLPIzhdIkqXkerFOm2CaD/5bcKrjIL2c3fkhPxOq93Kcb91v46fV9TQKF4TgV/TbUsQtzfCaK6jMOd5DJrguSIIhexmqqVxN0FXbRR8/ND/LYTTj6J7nl2gnL47OkDW4KJhnQHCa6JpKVNJGA3OC58nwBJoZ//ebbIyKpBxjrr0o1q1FMRkrKXZnHWF85VvxMrJxibwhGyd0f5bLnKzqJs1k0Sfo+EU8hdAUvkbcwKEgs2D0OiV4jmmD1zb+Tp6er0JMMvDxPo5xev9zTBF683NS+N56n1YiB95B5crr93KRuKhKI0tb0Kw2mgLLqTjLEWO8424i9IvURaYeOckwf3+/yCC9e3bQQ/MuD+Monk0k+XFXMUfx7z5EEP+XlXi5tLlMxH8zLppw7idJrugcus30kC86gc7UrQqjLIukM8zWHOACeU+TiMxXN6ExVOkgz4lvPEzice1GIVhxhG4CrZvpl6TH55giKWqXGLy9hZh5aUtgDSew/msSyCKpl+DDNfxJc8NBIsxUxUnz14O/oONu+IIIvso9TLBQ1SY5rUhuSzUhAqJ2mRXBLDOCeUtgUZXsaObT8BffhUJPqWgiV+3zKKzYH0ClvTRLhD77HIqVkyh5jThnivehoG+qJctIRSPn6bxvO4FCgTl9c1DmbpjLajbQFE8aW5SU3rg+zOPGUjTUF9NFpLEbH2c/KmGYlY69/GQJVtGMSUcEp9eCbB1nctbxHTLRdTUkGDf+B02uGWRG3OvpJ/zSMwzif+oxVBID3cQKBavLCiPmB2PM2UuSCUPgrX4VDb97AwEG67bh4+KTOlncvu3M31BwA5rLHbCfEjwkNDky9e/SSbSxnD46Pg0RJtpXRvhmBSZHpRjWtKwFybjuQeXaKxto4WjLZZZvVmC17pZLJFkwxm5++PS2Mrwc7nyIMYZe/IzoP5d6QgEybqTXAAAAAElFTkSuQmCC',
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
