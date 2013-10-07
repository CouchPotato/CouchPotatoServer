import re
import json
import itertools

from .common import InfoExtractor
from .subtitles import SubtitlesInfoExtractor

from ..utils import (
    compat_urllib_request,
    compat_str,
    get_element_by_attribute,
    get_element_by_id,

    ExtractorError,
)

class DailymotionBaseInfoExtractor(InfoExtractor):
    @staticmethod
    def _build_request(url):
        """Build a request with the family filter disabled"""
        request = compat_urllib_request.Request(url)
        request.add_header('Cookie', 'family_filter=off')
        return request

class DailymotionIE(DailymotionBaseInfoExtractor, SubtitlesInfoExtractor):
    """Information Extractor for Dailymotion"""

    _VALID_URL = r'(?i)(?:https?://)?(?:www\.)?dailymotion\.[a-z]{2,3}/(?:embed/)?video/([^/]+)'
    IE_NAME = u'dailymotion'
    _TESTS = [
        {
            u'url': u'http://www.dailymotion.com/video/x33vw9_tutoriel-de-youtubeur-dl-des-video_tech',
            u'file': u'x33vw9.mp4',
            u'md5': u'392c4b85a60a90dc4792da41ce3144eb',
            u'info_dict': {
                u"uploader": u"Amphora Alex and Van .", 
                u"title": u"Tutoriel de Youtubeur\"DL DES VIDEO DE YOUTUBE\""
            }
        },
        # Vevo video
        {
            u'url': u'http://www.dailymotion.com/video/x149uew_katy-perry-roar-official_musi',
            u'file': u'USUV71301934.mp4',
            u'info_dict': {
                u'title': u'Roar (Official)',
                u'uploader': u'Katy Perry',
                u'upload_date': u'20130905',
            },
            u'params': {
                u'skip_download': True,
            },
            u'skip': u'VEVO is only available in some countries',
        },
    ]

    def _real_extract(self, url):
        # Extract id and simplified title from URL
        mobj = re.match(self._VALID_URL, url)

        video_id = mobj.group(1).split('_')[0].split('?')[0]

        video_extension = 'mp4'
        url = 'http://www.dailymotion.com/video/%s' % video_id

        # Retrieve video webpage to extract further information
        request = self._build_request(url)
        webpage = self._download_webpage(request, video_id)

        # Extract URL, uploader and title from webpage
        self.report_extraction(video_id)

        # It may just embed a vevo video:
        m_vevo = re.search(
            r'<link rel="video_src" href="[^"]*?vevo.com[^"]*?videoId=(?P<id>[\w]*)',
            webpage)
        if m_vevo is not None:
            vevo_id = m_vevo.group('id')
            self.to_screen(u'Vevo video detected: %s' % vevo_id)
            return self.url_result(u'vevo:%s' % vevo_id, ie='Vevo')

        video_uploader = self._search_regex([r'(?im)<span class="owner[^\"]+?">[^<]+?<a [^>]+?>([^<]+?)</a>',
                                             # Looking for official user
                                             r'<(?:span|a) .*?rel="author".*?>([^<]+?)</'],
                                            webpage, 'video uploader')

        video_upload_date = None
        mobj = re.search(r'<div class="[^"]*uploaded_cont[^"]*" title="[^"]*">([0-9]{2})-([0-9]{2})-([0-9]{4})</div>', webpage)
        if mobj is not None:
            video_upload_date = mobj.group(3) + mobj.group(2) + mobj.group(1)

        embed_url = 'http://www.dailymotion.com/embed/video/%s' % video_id
        embed_page = self._download_webpage(embed_url, video_id,
                                            u'Downloading embed page')
        info = self._search_regex(r'var info = ({.*?}),$', embed_page,
            'video info', flags=re.MULTILINE)
        info = json.loads(info)
        if info.get('error') is not None:
            msg = 'Couldn\'t get video, Dailymotion says: %s' % info['error']['title']
            raise ExtractorError(msg, expected=True)

        # TODO: support choosing qualities

        for key in ['stream_h264_hd1080_url','stream_h264_hd_url',
                    'stream_h264_hq_url','stream_h264_url',
                    'stream_h264_ld_url']:
            if info.get(key):#key in info and info[key]:
                max_quality = key
                self.to_screen(u'Using %s' % key)
                break
        else:
            raise ExtractorError(u'Unable to extract video URL')
        video_url = info[max_quality]

        # subtitles
        video_subtitles = self.extract_subtitles(video_id)
        if self._downloader.params.get('listsubtitles', False):
            self._list_available_subtitles(video_id)
            return

        return [{
            'id':       video_id,
            'url':      video_url,
            'uploader': video_uploader,
            'upload_date':  video_upload_date,
            'title':    self._og_search_title(webpage),
            'ext':      video_extension,
            'subtitles':    video_subtitles,
            'thumbnail': info['thumbnail_url']
        }]

    def _get_available_subtitles(self, video_id):
        try:
            sub_list = self._download_webpage(
                'https://api.dailymotion.com/video/%s/subtitles?fields=id,language,url' % video_id,
                video_id, note=False)
        except ExtractorError as err:
            self._downloader.report_warning(u'unable to download video subtitles: %s' % compat_str(err))
            return {}
        info = json.loads(sub_list)
        if (info['total'] > 0):
            sub_lang_list = dict((l['language'], l['url']) for l in info['list'])
            return sub_lang_list
        self._downloader.report_warning(u'video doesn\'t have subtitles')
        return {}


class DailymotionPlaylistIE(DailymotionBaseInfoExtractor):
    IE_NAME = u'dailymotion:playlist'
    _VALID_URL = r'(?:https?://)?(?:www\.)?dailymotion\.[a-z]{2,3}/playlist/(?P<id>.+?)/'
    _MORE_PAGES_INDICATOR = r'<div class="next">.*?<a.*?href="/playlist/.+?".*?>.*?</a>.*?</div>'
    _PAGE_TEMPLATE = 'https://www.dailymotion.com/playlist/%s/%s'

    def _extract_entries(self, id):
        video_ids = []
        for pagenum in itertools.count(1):
            request = self._build_request(self._PAGE_TEMPLATE % (id, pagenum))
            webpage = self._download_webpage(request,
                                             id, u'Downloading page %s' % pagenum)

            playlist_el = get_element_by_attribute(u'class', u'video_list', webpage)
            video_ids.extend(re.findall(r'data-id="(.+?)" data-ext-id', playlist_el))

            if re.search(self._MORE_PAGES_INDICATOR, webpage, re.DOTALL) is None:
                break
        return [self.url_result('http://www.dailymotion.com/video/%s' % video_id, 'Dailymotion')
                   for video_id in video_ids]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        playlist_id = mobj.group('id')
        webpage = self._download_webpage(url, playlist_id)

        return {'_type': 'playlist',
                'id': playlist_id,
                'title': get_element_by_id(u'playlist_name', webpage),
                'entries': self._extract_entries(playlist_id),
                }


class DailymotionUserIE(DailymotionPlaylistIE):
    IE_NAME = u'dailymotion:user'
    _VALID_URL = r'(?:https?://)?(?:www\.)?dailymotion\.[a-z]{2,3}/user/(?P<user>[^/]+)'
    _MORE_PAGES_INDICATOR = r'<div class="next">.*?<a.*?href="/user/.+?".*?>.*?</a>.*?</div>'
    _PAGE_TEMPLATE = 'http://www.dailymotion.com/user/%s/%s'

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        user = mobj.group('user')
        webpage = self._download_webpage(url, user)
        full_user = self._html_search_regex(
            r'<a class="label" href="/%s".*?>(.*?)</' % re.escape(user),
            webpage, u'user', flags=re.DOTALL)

        return {
            '_type': 'playlist',
            'id': user,
            'title': full_user,
            'entries': self._extract_entries(user),
        }
