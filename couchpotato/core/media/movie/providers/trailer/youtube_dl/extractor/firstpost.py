from __future__ import unicode_literals

import re

from .common import InfoExtractor


class FirstpostIE(InfoExtractor):
    _VALID_URL = r'http://(?:www\.)?firstpost\.com/[^/]+/.*-(?P<id>[0-9]+)\.html'

    _TEST = {
        'url': 'http://www.firstpost.com/india/india-to-launch-indigenous-aircraft-carrier-monday-1025403.html',
        'md5': 'ee9114957692f01fb1263ed87039112a',
        'info_dict': {
            'id': '1025403',
            'ext': 'mp4',
            'title': 'India to launch indigenous aircraft carrier INS Vikrant today',
        }
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        data = self._download_xml(
            'http://www.firstpost.com/getvideoxml-%s.xml' % video_id, video_id,
            'Downloading video XML')

        item = data.find('./playlist/item')
        thumbnail = item.find('./image').text
        title = item.find('./title').text

        formats = [
            {
                'url': details.find('./file').text,
                'format_id': details.find('./label').text.strip(),
                'width': int(details.find('./width').text.strip()),
                'height': int(details.find('./height').text.strip()),
            } for details in item.findall('./source/file_details') if details.find('./file').text
        ]

        return {
            'id': video_id,
            'title': title,
            'thumbnail': thumbnail,
            'formats': formats,
        }
