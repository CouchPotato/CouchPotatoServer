import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    compat_parse_qs,
)


class Ro220IE(InfoExtractor):
    IE_NAME = '220.ro'
    _VALID_URL = r'(?x)(?:https?://)?(?:www\.)?220\.ro/(?P<category>[^/]+)/(?P<shorttitle>[^/]+)/(?P<video_id>[^/]+)'
    _TEST = {
        u"url": u"http://www.220.ro/sport/Luati-Le-Banii-Sez-4-Ep-1/LYV6doKo7f/",
        u'file': u'LYV6doKo7f.mp4',
        u'md5': u'03af18b73a07b4088753930db7a34add',
        u'info_dict': {
            u"title": u"Luati-le Banii sez 4 ep 1",
            u"description": u"Iata-ne reveniti dupa o binemeritata vacanta. Va astept si pe Facebook cu pareri si comentarii.",
        }
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('video_id')

        webpage = self._download_webpage(url, video_id)
        flashVars_str = self._search_regex(
            r'<param name="flashVars" value="([^"]+)"',
            webpage, u'flashVars')
        flashVars = compat_parse_qs(flashVars_str)

        info = {
            '_type': 'video',
            'id': video_id,
            'ext': 'mp4',
            'url': flashVars['videoURL'][0],
            'title': flashVars['title'][0],
            'description': clean_html(flashVars['desc'][0]),
            'thumbnail': flashVars['preview'][0],
        }
        return info
