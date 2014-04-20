# encoding: utf-8
from __future__ import unicode_literals

import re

from hashlib import sha1
from .common import InfoExtractor
from ..utils import (
    compat_urllib_parse,
    unified_strdate,
    clean_html,
    RegexNotFoundError,
)


class ProSiebenSat1IE(InfoExtractor):
    IE_NAME = 'prosiebensat1'
    IE_DESC = 'ProSiebenSat.1 Digital'
    _VALID_URL = r'https?://(?:www\.)?(?:(?:prosieben|prosiebenmaxx|sixx|sat1|kabeleins|ran|the-voice-of-germany)\.de|fem\.com)/(?P<id>.+)'

    _TESTS = [
        {
            'url': 'http://www.prosieben.de/tv/circus-halligalli/videos/218-staffel-2-episode-18-jahresrueckblick-ganze-folge',
            'info_dict': {
                'id': '2104602',
                'ext': 'mp4',
                'title': 'Staffel 2, Episode 18 - Jahresrückblick',
                'description': 'md5:8733c81b702ea472e069bc48bb658fc1',
                'upload_date': '20131231',
                'duration': 5845.04,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.prosieben.de/videokatalog/Gesellschaft/Leben/Trends/video-Lady-Umstyling-f%C3%BCr-Audrina-Rebekka-Audrina-Fergen-billig-aussehen-Battal-Modica-700544.html',
            'info_dict': {
                'id': '2570327',
                'ext': 'mp4',
                'title': 'Lady-Umstyling für Audrina',
                'description': 'md5:4c16d0c17a3461a0d43ea4084e96319d',
                'upload_date': '20131014',
                'duration': 606.76,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
            'skip': 'Seems to be broken',
        },
        {
            'url': 'http://www.prosiebenmaxx.de/tv/experience/video/144-countdown-fuer-die-autowerkstatt-ganze-folge',
            'info_dict': {
                'id': '2429369',
                'ext': 'mp4',
                'title': 'Countdown für die Autowerkstatt',
                'description': 'md5:809fc051a457b5d8666013bc40698817',
                'upload_date': '20140223',
                'duration': 2595.04,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.sixx.de/stars-style/video/sexy-laufen-in-ugg-boots-clip',
            'info_dict': {
                'id': '2904997',
                'ext': 'mp4',
                'title': 'Sexy laufen in Ugg Boots',
                'description': 'md5:edf42b8bd5bc4e5da4db4222c5acb7d6',
                'upload_date': '20140122',
                'duration': 245.32,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.sat1.de/film/der-ruecktritt/video/im-interview-kai-wiesinger-clip',
            'info_dict': {
                'id': '2906572',
                'ext': 'mp4',
                'title': 'Im Interview: Kai Wiesinger',
                'description': 'md5:e4e5370652ec63b95023e914190b4eb9',
                'upload_date': '20140225',
                'duration': 522.56,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.kabeleins.de/tv/rosins-restaurants/videos/jagd-auf-fertigkost-im-elsthal-teil-2-ganze-folge',
            'info_dict': {
                'id': '2992323',
                'ext': 'mp4',
                'title': 'Jagd auf Fertigkost im Elsthal - Teil 2',
                'description': 'md5:2669cde3febe9bce13904f701e774eb6',
                'upload_date': '20140225',
                'duration': 2410.44,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.ran.de/fussball/bundesliga/video/schalke-toennies-moechte-raul-zurueck-ganze-folge',
            'info_dict': {
                'id': '3004256',
                'ext': 'mp4',
                'title': 'Schalke: Tönnies möchte Raul zurück',
                'description': 'md5:4b5b271d9bcde223b54390754c8ece3f',
                'upload_date': '20140226',
                'duration': 228.96,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.the-voice-of-germany.de/video/31-andreas-kuemmert-rocket-man-clip',
            'info_dict': {
                'id': '2572814',
                'ext': 'mp4',
                'title': 'Andreas Kümmert: Rocket Man',
                'description': 'md5:6ddb02b0781c6adf778afea606652e38',
                'upload_date': '20131017',
                'duration': 469.88,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.fem.com/wellness/videos/wellness-video-clip-kurztripps-zum-valentinstag.html',
            'info_dict': {
                'id': '2156342',
                'ext': 'mp4',
                'title': 'Kurztrips zum Valentinstag',
                'description': 'md5:8ba6301e70351ae0bedf8da00f7ba528',
                'upload_date': '20130206',
                'duration': 307.24,
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
    ]

    _CLIPID_REGEXES = [
        r'"clip_id"\s*:\s+"(\d+)"',
        r'clipid: "(\d+)"',
        r'clipId=(\d+)',
    ]
    _TITLE_REGEXES = [
        r'<h2 class="subtitle" itemprop="name">\s*(.+?)</h2>',
        r'<header class="clearfix">\s*<h3>(.+?)</h3>',
        r'<!-- start video -->\s*<h1>(.+?)</h1>',
        r'<div class="ep-femvideos-pi4-video-txt">\s*<h2>(.+?)</h2>',
    ]
    _DESCRIPTION_REGEXES = [
        r'<p itemprop="description">\s*(.+?)</p>',
        r'<div class="videoDecription">\s*<p><strong>Beschreibung</strong>: (.+?)</p>',
        r'<div class="g-plusone" data-size="medium"></div>\s*</div>\s*</header>\s*(.+?)\s*<footer>',
        r'<p>(.+?)</p>\s*<div class="ep-femvideos-pi4-video-footer">',
    ]
    _UPLOAD_DATE_REGEXES = [
        r'<meta property="og:published_time" content="(.+?)">',
        r'<span>\s*(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}) \|\s*<span itemprop="duration"',
        r'<footer>\s*(\d{2}\.\d{2}\.\d{4}) \d{2}:\d{2} Uhr',
        r'<span style="padding-left: 4px;line-height:20px; color:#404040">(\d{2}\.\d{2}\.\d{4})</span>',
        r'(\d{2}\.\d{2}\.\d{4}) \| \d{2}:\d{2} Min<br/>',
    ]

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')

        page = self._download_webpage(url, video_id, 'Downloading page')

        def extract(patterns, name, page, fatal=False):
            for pattern in patterns:
                mobj = re.search(pattern, page)
                if mobj:
                    return clean_html(mobj.group(1))
            if fatal:
                raise RegexNotFoundError(u'Unable to extract %s' % name)
            return None

        clip_id = extract(self._CLIPID_REGEXES, 'clip id', page, fatal=True)

        access_token = 'testclient'
        client_name = 'kolibri-1.2.5'
        client_location = url

        videos_api_url = 'http://vas.sim-technik.de/vas/live/v2/videos?%s' % compat_urllib_parse.urlencode({
            'access_token': access_token,
            'client_location': client_location,
            'client_name': client_name,
            'ids': clip_id,
        })

        videos = self._download_json(videos_api_url, clip_id, 'Downloading videos JSON')

        duration = float(videos[0]['duration'])
        source_ids = [source['id'] for source in videos[0]['sources']]
        source_ids_str = ','.join(map(str, source_ids))

        g = '01!8d8F_)r9]4s[qeuXfP%'

        client_id = g[:2] + sha1(''.join([clip_id, g, access_token, client_location, g, client_name])
                                 .encode('utf-8')).hexdigest()

        sources_api_url = 'http://vas.sim-technik.de/vas/live/v2/videos/%s/sources?%s' % (clip_id, compat_urllib_parse.urlencode({
            'access_token': access_token,
            'client_id': client_id,
            'client_location': client_location,
            'client_name': client_name,
        }))

        sources = self._download_json(sources_api_url, clip_id, 'Downloading sources JSON')
        server_id = sources['server_id']

        client_id = g[:2] + sha1(''.join([g, clip_id, access_token, server_id,
                                          client_location, source_ids_str, g, client_name])
                                 .encode('utf-8')).hexdigest()

        url_api_url = 'http://vas.sim-technik.de/vas/live/v2/videos/%s/sources/url?%s' % (clip_id, compat_urllib_parse.urlencode({
            'access_token': access_token,
            'client_id': client_id,
            'client_location': client_location,
            'client_name': client_name,
            'server_id': server_id,
            'source_ids': source_ids_str,
        }))

        urls = self._download_json(url_api_url, clip_id, 'Downloading urls JSON')

        title = extract(self._TITLE_REGEXES, 'title', page, fatal=True)
        description = extract(self._DESCRIPTION_REGEXES, 'description', page)
        thumbnail = self._og_search_thumbnail(page)

        upload_date = extract(self._UPLOAD_DATE_REGEXES, 'upload date', page)
        if upload_date:
            upload_date = unified_strdate(upload_date)

        formats = []

        urls_sources = urls['sources']
        if isinstance(urls_sources, dict):
            urls_sources = urls_sources.values()

        def fix_bitrate(bitrate):
            return bitrate / 1000 if bitrate % 1000 == 0 else bitrate

        for source in urls_sources:
            protocol = source['protocol']
            if protocol == 'rtmp' or protocol == 'rtmpe':
                mobj = re.search(r'^(?P<url>rtmpe?://[^/]+/(?P<app>[^/]+))/(?P<playpath>.+)$', source['url'])
                if not mobj:
                    continue
                formats.append({
                    'url': mobj.group('url'),
                    'app': mobj.group('app'),
                    'play_path': mobj.group('playpath'),
                    'player_url': 'http://livepassdl.conviva.com/hf/ver/2.79.0.17083/LivePassModuleMain.swf',
                    'page_url': 'http://www.prosieben.de',
                    'vbr': fix_bitrate(source['bitrate']),
                    'ext': 'mp4',
                    'format_id': '%s_%s' % (source['cdn'], source['bitrate']),
                })
            else:
                formats.append({
                    'url': source['url'],
                    'vbr': fix_bitrate(source['bitrate']),
                })

        self._sort_formats(formats)

        return {
            'id': clip_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'upload_date': upload_date,
            'duration': duration,
            'formats': formats,
        }