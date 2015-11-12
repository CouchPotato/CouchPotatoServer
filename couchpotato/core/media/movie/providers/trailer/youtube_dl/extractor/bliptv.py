from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .subtitles import SubtitlesInfoExtractor

from ..compat import (
    compat_str,
    compat_urllib_request,
    compat_urlparse,
)
from ..utils import (
    clean_html,
    int_or_none,
    parse_iso8601,
    unescapeHTML,
)


class BlipTVIE(SubtitlesInfoExtractor):
    _VALID_URL = r'https?://(?:\w+\.)?blip\.tv/(?:(?:.+-|rss/flash/)(?P<id>\d+)|((?:play/|api\.swf#)(?P<lookup_id>[\da-zA-Z+_]+)))'

    _TESTS = [
        {
            'url': 'http://blip.tv/cbr/cbr-exclusive-gotham-city-imposters-bats-vs-jokerz-short-3-5796352',
            'md5': 'c6934ad0b6acf2bd920720ec888eb812',
            'info_dict': {
                'id': '5779306',
                'ext': 'mov',
                'title': 'CBR EXCLUSIVE: "Gotham City Imposters" Bats VS Jokerz Short 3',
                'description': 'md5:9bc31f227219cde65e47eeec8d2dc596',
                'timestamp': 1323138843,
                'upload_date': '20111206',
                'uploader': 'cbr',
                'uploader_id': '679425',
                'duration': 81,
            }
        },
        {
            # https://github.com/rg3/youtube-dl/pull/2274
            'note': 'Video with subtitles',
            'url': 'http://blip.tv/play/h6Uag5OEVgI.html',
            'md5': '309f9d25b820b086ca163ffac8031806',
            'info_dict': {
                'id': '6586561',
                'ext': 'mp4',
                'title': 'Red vs. Blue Season 11 Episode 1',
                'description': 'One-Zero-One',
                'timestamp': 1371261608,
                'upload_date': '20130615',
                'uploader': 'redvsblue',
                'uploader_id': '792887',
                'duration': 279,
            }
        },
        {
            # https://bugzilla.redhat.com/show_bug.cgi?id=967465
            'url': 'http://a.blip.tv/api.swf#h6Uag5KbVwI',
            'md5': '314e87b1ebe7a48fcbfdd51b791ce5a6',
            'info_dict': {
                'id': '6573122',
                'ext': 'mov',
                'upload_date': '20130520',
                'description': 'Two hapless space marines argue over what to do when they realize they have an astronomically huge problem on their hands.',
                'title': 'Red vs. Blue Season 11 Trailer',
                'timestamp': 1369029609,
                'uploader': 'redvsblue',
                'uploader_id': '792887',
            }
        },
        {
            'url': 'http://blip.tv/play/gbk766dkj4Yn',
            'md5': 'fe0a33f022d49399a241e84a8ea8b8e3',
            'info_dict': {
                'id': '1749452',
                'ext': 'mp4',
                'upload_date': '20090208',
                'description': 'Witness the first appearance of the Nostalgia Critic character, as Doug reviews the movie Transformers.',
                'title': 'Nostalgia Critic: Transformers',
                'timestamp': 1234068723,
                'uploader': 'NostalgiaCritic',
                'uploader_id': '246467',
            }
        },
        {
            # https://github.com/rg3/youtube-dl/pull/4404
            'note': 'Audio only',
            'url': 'http://blip.tv/hilarios-productions/weekly-manga-recap-kingdom-7119982',
            'md5': '76c0a56f24e769ceaab21fbb6416a351',
            'info_dict': {
                'id': '7103299',
                'ext': 'flv',
                'title': 'Weekly Manga Recap: Kingdom',
                'description': 'And then Shin breaks the enemy line, and he&apos;s all like HWAH! And then he slices a guy and it&apos;s all like FWASHING! And... it&apos;s really hard to describe the best parts of this series without breaking down into sound effects, okay?',
                'timestamp': 1417660321,
                'upload_date': '20141204',
                'uploader': 'The Rollo T',
                'uploader_id': '407429',
                'duration': 7251,
                'vcodec': 'none',
            }
        },
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        lookup_id = mobj.group('lookup_id')

        # See https://github.com/rg3/youtube-dl/issues/857 and
        # https://github.com/rg3/youtube-dl/issues/4197
        if lookup_id:
            urlh = self._request_webpage(
                'http://blip.tv/play/%s' % lookup_id, lookup_id, 'Resolving lookup id')
            url = compat_urlparse.urlparse(urlh.geturl())
            qs = compat_urlparse.parse_qs(url.query)
            mobj = re.match(self._VALID_URL, qs['file'][0])

        video_id = mobj.group('id')

        rss = self._download_xml('http://blip.tv/rss/flash/%s' % video_id, video_id, 'Downloading video RSS')

        def blip(s):
            return '{http://blip.tv/dtd/blip/1.0}%s' % s

        def media(s):
            return '{http://search.yahoo.com/mrss/}%s' % s

        def itunes(s):
            return '{http://www.itunes.com/dtds/podcast-1.0.dtd}%s' % s

        item = rss.find('channel/item')

        video_id = item.find(blip('item_id')).text
        title = item.find('./title').text
        description = clean_html(compat_str(item.find(blip('puredescription')).text))
        timestamp = parse_iso8601(item.find(blip('datestamp')).text)
        uploader = item.find(blip('user')).text
        uploader_id = item.find(blip('userid')).text
        duration = int(item.find(blip('runtime')).text)
        media_thumbnail = item.find(media('thumbnail'))
        thumbnail = media_thumbnail.get('url') if media_thumbnail is not None else item.find(itunes('image')).text
        categories = [category.text for category in item.findall('category')]

        formats = []
        subtitles = {}

        media_group = item.find(media('group'))
        for media_content in media_group.findall(media('content')):
            url = media_content.get('url')
            role = media_content.get(blip('role'))
            msg = self._download_webpage(
                url + '?showplayer=20140425131715&referrer=http://blip.tv&mask=7&skin=flashvars&view=url',
                video_id, 'Resolving URL for %s' % role)
            real_url = compat_urlparse.parse_qs(msg.strip())['message'][0]

            media_type = media_content.get('type')
            if media_type == 'text/srt' or url.endswith('.srt'):
                LANGS = {
                    'english': 'en',
                }
                lang = role.rpartition('-')[-1].strip().lower()
                langcode = LANGS.get(lang, lang)
                subtitles[langcode] = url
            elif media_type.startswith('video/'):
                formats.append({
                    'url': real_url,
                    'format_id': role,
                    'format_note': media_type,
                    'vcodec': media_content.get(blip('vcodec')) or 'none',
                    'acodec': media_content.get(blip('acodec')),
                    'filesize': media_content.get('filesize'),
                    'width': int_or_none(media_content.get('width')),
                    'height': int_or_none(media_content.get('height')),
                })
        self._sort_formats(formats)

        # subtitles
        video_subtitles = self.extract_subtitles(video_id, subtitles)
        if self._downloader.params.get('listsubtitles', False):
            self._list_available_subtitles(video_id, subtitles)
            return

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'timestamp': timestamp,
            'uploader': uploader,
            'uploader_id': uploader_id,
            'duration': duration,
            'thumbnail': thumbnail,
            'categories': categories,
            'formats': formats,
            'subtitles': video_subtitles,
        }

    def _download_subtitle_url(self, sub_lang, url):
        # For some weird reason, blip.tv serves a video instead of subtitles
        # when we request with a common UA
        req = compat_urllib_request.Request(url)
        req.add_header('Youtubedl-user-agent', 'youtube-dl')
        return self._download_webpage(req, None, note=False)


class BlipTVUserIE(InfoExtractor):
    _VALID_URL = r'(?:(?:https?://(?:\w+\.)?blip\.tv/)|bliptvuser:)(?!api\.swf)([^/]+)/*$'
    _PAGE_SIZE = 12
    IE_NAME = 'blip.tv:user'
    _TEST = {
        'url': 'http://blip.tv/actone',
        'info_dict': {
            'id': 'actone',
            'title': 'Act One: The Series',
        },
        'playlist_count': 5,
    }

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        username = mobj.group(1)

        page_base = 'http://m.blip.tv/pr/show_get_full_episode_list?users_id=%s&lite=0&esi=1'

        page = self._download_webpage(url, username, 'Downloading user page')
        mobj = re.search(r'data-users-id="([^"]+)"', page)
        page_base = page_base % mobj.group(1)
        title = self._og_search_title(page)

        # Download video ids using BlipTV Ajax calls. Result size per
        # query is limited (currently to 12 videos) so we need to query
        # page by page until there are no video ids - it means we got
        # all of them.

        video_ids = []
        pagenum = 1

        while True:
            url = page_base + "&page=" + str(pagenum)
            page = self._download_webpage(
                url, username, 'Downloading video ids from page %d' % pagenum)

            # Extract video identifiers
            ids_in_page = []

            for mobj in re.finditer(r'href="/([^"]+)"', page):
                if mobj.group(1) not in ids_in_page:
                    ids_in_page.append(unescapeHTML(mobj.group(1)))

            video_ids.extend(ids_in_page)

            # A little optimization - if current page is not
            # "full", ie. does not contain PAGE_SIZE video ids then
            # we can assume that this page is the last one - there
            # are no more ids on further pages - no need to query
            # again.

            if len(ids_in_page) < self._PAGE_SIZE:
                break

            pagenum += 1

        urls = ['http://blip.tv/%s' % video_id for video_id in video_ids]
        url_entries = [self.url_result(vurl, 'BlipTV') for vurl in urls]
        return self.playlist_result(
            url_entries, playlist_title=title, playlist_id=username)
