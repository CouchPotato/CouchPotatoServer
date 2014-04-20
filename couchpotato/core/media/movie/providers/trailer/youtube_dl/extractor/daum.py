# encoding: utf-8

from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    compat_urllib_parse,
)


class DaumIE(InfoExtractor):
    _VALID_URL = r'https?://(?:m\.)?tvpot\.daum\.net/.*?clipid=(?P<id>\d+)'
    IE_NAME = 'daum.net'

    _TEST = {
        'url': 'http://tvpot.daum.net/clip/ClipView.do?clipid=52554690',
        'info_dict': {
            'id': '52554690',
            'ext': 'mp4',
            'title': 'DOTA 2GETHER 시즌2 6회 - 2부',
            'description': 'DOTA 2GETHER 시즌2 6회 - 2부',
            'upload_date': '20130831',
            'duration': 3868,
        },
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group(1)
        canonical_url = 'http://tvpot.daum.net/v/%s' % video_id
        webpage = self._download_webpage(canonical_url, video_id)
        full_id = self._search_regex(
            r'<iframe src="http://videofarm.daum.net/controller/video/viewer/Video.html\?.*?vid=(.+?)[&"]',
            webpage, 'full id')
        query = compat_urllib_parse.urlencode({'vid': full_id})
        info = self._download_xml(
            'http://tvpot.daum.net/clip/ClipInfoXml.do?' + query, video_id,
            'Downloading video info')
        urls = self._download_xml(
            'http://videofarm.daum.net/controller/api/open/v1_2/MovieData.apixml?' + query,
            video_id, 'Downloading video formats info')

        self.to_screen(u'%s: Getting video urls' % video_id)
        formats = []
        for format_el in urls.findall('result/output_list/output_list'):
            profile = format_el.attrib['profile']
            format_query = compat_urllib_parse.urlencode({
                'vid': full_id,
                'profile': profile,
            })
            url_doc = self._download_xml(
                'http://videofarm.daum.net/controller/api/open/v1_2/MovieLocation.apixml?' + format_query,
                video_id, note=False)
            format_url = url_doc.find('result/url').text
            formats.append({
                'url': format_url,
                'format_id': profile,
            })

        return {
            'id': video_id,
            'title': info.find('TITLE').text,
            'formats': formats,
            'thumbnail': self._og_search_thumbnail(webpage),
            'description': info.find('CONTENTS').text,
            'duration': int(info.find('DURATION').text),
            'upload_date': info.find('REGDTTM').text[:8],
        }
