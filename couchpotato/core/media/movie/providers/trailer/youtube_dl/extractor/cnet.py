# coding: utf-8
from __future__ import unicode_literals

import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
)


class CNETIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?cnet\.com/videos/(?P<id>[^/]+)/'
    _TEST = {
        'url': 'http://www.cnet.com/videos/hands-on-with-microsofts-windows-8-1-update/',
        'info_dict': {
            'id': '56f4ea68-bd21-4852-b08c-4de5b8354c60',
            'ext': 'flv',
            'title': 'Hands-on with Microsoft Windows 8.1 Update',
            'description': 'The new update to the Windows 8 OS brings improved performance for mouse and keyboard users.',
            'thumbnail': 're:^http://.*/flmswindows8.jpg$',
            'uploader_id': '6085384d-619e-11e3-b231-14feb5ca9861',
            'uploader': 'Sarah Mitroff',
        },
        'params': {
            'skip_download': 'requires rtmpdump',
        }
    }

    def _real_extract(self, url):
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)

        data_json = self._html_search_regex(
            r"<div class=\"cnetVideoPlayer\"\s+.*?data-cnet-video-options='([^']+)'",
            webpage, 'data json')
        data = json.loads(data_json)
        vdata = data['video']
        if not vdata:
            vdata = data['videos'][0]
        if not vdata:
            raise ExtractorError('Cannot find video data')

        mpx_account = data['config']['players']['default']['mpx_account']
        vid = vdata['files']['rtmp']
        tp_link = 'http://link.theplatform.com/s/%s/%s' % (mpx_account, vid)

        video_id = vdata['id']
        title = vdata.get('headline')
        if title is None:
            title = vdata.get('title')
        if title is None:
            raise ExtractorError('Cannot find title!')
        thumbnail = vdata.get('image', {}).get('path')
        author = vdata.get('author')
        if author:
            uploader = '%s %s' % (author['firstName'], author['lastName'])
            uploader_id = author.get('id')
        else:
            uploader = None
            uploader_id = None

        return {
            '_type': 'url_transparent',
            'url': tp_link,
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'thumbnail': thumbnail,
        }
