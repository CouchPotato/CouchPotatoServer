from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.base import NZBProvider


log = CPLog(__name__)


class Base(NZBProvider, RSS):

    urls = {
        'search': 'https://api.omgwtfnzbs.me/json/?%s',
    }

    http_time_between_calls = 1   # Seconds

    cat_ids = [
        ([15], ['dvdrip', 'scr', 'r5', 'tc', 'ts', 'cam']),
        ([15, 16], ['brrip']),
        ([16], ['720p', '1080p', 'bd50']),
        ([17], ['dvdr']),
    ]
    cat_backup_id = 'movie'

    def _searchOnTitle(self, title, movie, quality, results):

        q = '%s %s' % (title, movie['info']['year'])
        params = tryUrlencode({
            'search': q,
            'catid': ','.join([str(x) for x in self.getCatId(quality)]),
            'user': self.conf('username', default = ''),
            'api': self.conf('api_key', default = ''),
        })
        
        if len(self.conf('custom_tag')) > 0:
            params = '%s&%s' % (params, self.conf('custom_tag'))

        nzbs = self.getJsonData(self.urls['search'] % params)

        if isinstance(nzbs, list):
            for nzb in nzbs:

                results.append({
                    'id': nzb.get('nzbid'),
                    'name': toUnicode(nzb.get('release')),
                    'age': self.calculateAge(tryInt(nzb.get('usenetage'))),
                    'size': tryInt(nzb.get('sizebytes')) / 1024 / 1024,
                    'url': nzb.get('getnzb'),
                    'detail_url': nzb.get('details'),
                    'description': nzb.get('weblink')
                })


config = [{
    'name': 'omgwtfnzbs',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'OMGWTFNZBs',
            'description': 'See <a href="https://omgwtfnzbs.me/" target="_blank">OMGWTFNZBs</a>',
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
                    'name': 'custom_tag',
                    'advanced': True,
                    'label': 'Custom tag',
                    'default': '',
                    'description': 'Add custom parameters, for example add catid=18 to get foreign (non-english) movies',
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
