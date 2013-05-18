from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
import json
import traceback

log = CPLog(__name__)


class FTDWorld(NZBProvider):

    urls = {
        'search': 'http://ftdworld.net/api/index.php?%s',
        'detail': 'http://ftdworld.net/spotinfo.php?id=%s',
        'download': 'http://ftdworld.net/cgi-bin/nzbdown.pl?fileID=%s',
        'login': 'http://ftdworld.net/api/login.php',
    }

    http_time_between_calls = 3 #seconds

    cat_ids = [
        ([4, 11], ['dvdr']),
        ([1], ['cam', 'ts', 'dvdrip', 'tc', 'r5', 'scr', 'brrip']),
        ([7, 10, 13, 14], ['bd50', '720p', '1080p']),
    ]
    cat_backup_id = 1

    def _searchOnTitle(self, title, movie, quality, results):

        q = '"%s" %s' % (title, movie['library']['year'])

        params = tryUrlencode({
            'ctitle': q,
            'customQuery': 'usr',
            'cage': Env.setting('retention', 'nzb'),
            'csizemin': quality.get('size_min'),
            'csizemax': quality.get('size_max'),
            'ccategory': 14,
            'ctype': ','.join([str(x) for x in self.getCatId(quality['identifier'])]),
        })

        data = self.getJsonData(self.urls['search'] % params, opener = self.login_opener)

        if data:
            try:

                if data.get('numRes') == 0:
                    return

                for item in data.get('data'):

                    nzb_id = tryInt(item.get('id'))
                    results.append({
                        'id': nzb_id,
                        'name': toUnicode(item.get('Title')),
                        'age': self.calculateAge(tryInt(item.get('Created'))),
                        'size': item.get('Size', 0),
                        'url': self.urls['download'] % nzb_id,
                        'download': self.loginDownload,
                        'detail_url': self.urls['detail'] % nzb_id,
                        'score': (tryInt(item.get('webPlus', 0)) - tryInt(item.get('webMin', 0))) * 3,
                    })

            except:
                log.error('Failed to parse HTML response from FTDWorld: %s', traceback.format_exc())

    def getLoginParams(self):
        return tryUrlencode({
            'userlogin': self.conf('username'),
            'passlogin': self.conf('password'),
            'submit': 'Log In',
        })

    def loginSuccess(self, output):
        try:
            return json.loads(output).get('goodToGo', False)
        except:
            return False
