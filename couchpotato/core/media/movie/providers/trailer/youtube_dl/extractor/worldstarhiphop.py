from __future__ import unicode_literals

import re

from .common import InfoExtractor


class WorldStarHipHopIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www|m)\.worldstar(?:candy|hiphop)\.com/videos/video\.php\?v=(?P<id>.*)'
    _TEST = {
        "url": "http://www.worldstarhiphop.com/videos/video.php?v=wshh6a7q1ny0G34ZwuIO",
        "md5": "9d04de741161603bf7071bbf4e883186",
        "info_dict": {
            "id": "wshh6a7q1ny0G34ZwuIO",
            "ext": "mp4",
            "title": "Video: KO Of The Week: MMA Fighter Gets Knocked Out By Swift Head Kick!"
        }
    }

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url)
        video_id = m.group('id')

        webpage_src = self._download_webpage(url, video_id)

        m_vevo_id = re.search(r'videoId=(.*?)&amp?',
                              webpage_src)
        if m_vevo_id is not None:
            return self.url_result('vevo:%s' % m_vevo_id.group(1), ie='Vevo')

        video_url = self._search_regex(
            r'so\.addVariable\("file","(.*?)"\)', webpage_src, 'video URL')

        if 'youtube' in video_url:
            return self.url_result(video_url, ie='Youtube')

        video_title = self._html_search_regex(
            r"<title>(.*)</title>", webpage_src, 'title')

        # Getting thumbnail and if not thumbnail sets correct title for WSHH candy video.
        thumbnail = self._html_search_regex(
            r'rel="image_src" href="(.*)" />', webpage_src, 'thumbnail',
            fatal=False)
        if not thumbnail:
            _title = r"""candytitles.*>(.*)</span>"""
            mobj = re.search(_title, webpage_src)
            if mobj is not None:
                video_title = mobj.group(1)

        return {
            'id': video_id,
            'url': video_url,
            'title': video_title,
            'thumbnail': thumbnail,
        }

