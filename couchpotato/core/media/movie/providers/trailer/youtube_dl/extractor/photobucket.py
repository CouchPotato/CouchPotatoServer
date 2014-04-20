from __future__ import unicode_literals

import datetime
import json
import re

from .common import InfoExtractor


class PhotobucketIE(InfoExtractor):
    _VALID_URL = r'http://(?:[a-z0-9]+\.)?photobucket\.com/.*(([\?\&]current=)|_)(?P<id>.*)\.(?P<ext>(flv)|(mp4))'
    _TEST = {
        'url': 'http://media.photobucket.com/user/rachaneronas/media/TiredofLinkBuildingTryBacklinkMyDomaincom_zpsc0c3b9fa.mp4.html?filters[term]=search&filters[primary]=videos&filters[secondary]=images&sort=1&o=0',
        'file': 'zpsc0c3b9fa.mp4',
        'md5': '7dabfb92b0a31f6c16cebc0f8e60ff99',
        'info_dict': {
            'upload_date': '20130504',
            'uploader': 'rachaneronas',
            'title': 'Tired of Link Building? Try BacklinkMyDomain.com!',
        }
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        video_extension = mobj.group('ext')

        webpage = self._download_webpage(url, video_id)

        # Extract URL, uploader, and title from webpage
        self.report_extraction(video_id)
        info_json = self._search_regex(r'Pb\.Data\.Shared\.put\(Pb\.Data\.Shared\.MEDIA, (.*?)\);',
            webpage, 'info json')
        info = json.loads(info_json)
        return {
            'id': video_id,
            'url': info['downloadUrl'],
            'uploader': info['username'],
            'upload_date': datetime.date.fromtimestamp(info['creationDate']).strftime('%Y%m%d'),
            'title': info['title'],
            'ext': video_extension,
            'thumbnail': info['thumbUrl'],
        }
