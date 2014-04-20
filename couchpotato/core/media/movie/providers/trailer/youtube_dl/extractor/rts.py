# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import (
    int_or_none,
    parse_duration,
    parse_iso8601,
    unescapeHTML,
    compat_str,
)


class RTSIE(InfoExtractor):
    IE_DESC = 'RTS.ch'
    _VALID_URL = r'^https?://(?:www\.)?rts\.ch/(?:[^/]+/){2,}(?P<id>[0-9]+)-.*?\.html'

    _TESTS = [
        {
            'url': 'http://www.rts.ch/archives/tv/divers/3449373-les-enfants-terribles.html',
            'md5': '753b877968ad8afaeddccc374d4256a5',
            'info_dict': {
                'id': '3449373',
                'ext': 'mp4',
                'duration': 1488,
                'title': 'Les Enfants Terribles',
                'description': 'France Pommier et sa soeur Luce Feral, les deux filles de ce groupe de 5.',
                'uploader': 'Divers',
                'upload_date': '19680921',
                'timestamp': -40280400,
                'thumbnail': 're:^https?://.*\.image'
            },
        },
        {
            'url': 'http://www.rts.ch/emissions/passe-moi-les-jumelles/5624067-entre-ciel-et-mer.html',
            'md5': 'c148457a27bdc9e5b1ffe081a7a8337b',
            'info_dict': {
                'id': '5624067',
                'ext': 'mp4',
                'duration': 3720,
                'title': 'Les yeux dans les cieux - Mon homard au Canada',
                'description': 'md5:d22ee46f5cc5bac0912e5a0c6d44a9f7',
                'uploader': 'Passe-moi les jumelles',
                'upload_date': '20140404',
                'timestamp': 1396635300,
                'thumbnail': 're:^https?://.*\.image'
            },
        },
        {
            'url': 'http://www.rts.ch/video/sport/hockey/5745975-1-2-kloten-fribourg-5-2-second-but-pour-gotteron-par-kwiatowski.html',
            'md5': 'b4326fecd3eb64a458ba73c73e91299d',
            'info_dict': {
                'id': '5745975',
                'ext': 'mp4',
                'duration': 48,
                'title': '1/2, Kloten - Fribourg (5-2): second but pour Gottéron par Kwiatowski',
                'description': 'Hockey - Playoff',
                'uploader': 'Hockey',
                'upload_date': '20140403',
                'timestamp': 1396556882,
                'thumbnail': 're:^https?://.*\.image'
            },
            'skip': 'Blocked outside Switzerland',
        },
        {
            'url': 'http://www.rts.ch/video/info/journal-continu/5745356-londres-cachee-par-un-epais-smog.html',
            'md5': '9bb06503773c07ce83d3cbd793cebb91',
            'info_dict': {
                'id': '5745356',
                'ext': 'mp4',
                'duration': 33,
                'title': 'Londres cachée par un épais smog',
                'description': 'Un important voile de smog recouvre Londres depuis mercredi, provoqué par la pollution et du sable du Sahara.',
                'uploader': 'Le Journal en continu',
                'upload_date': '20140403',
                'timestamp': 1396537322,
                'thumbnail': 're:^https?://.*\.image'
            },
        },
        {
            'url': 'http://www.rts.ch/audio/couleur3/programmes/la-belle-video-de-stephane-laurenceau/5706148-urban-hippie-de-damien-krisl-03-04-2014.html',
            'md5': 'dd8ef6a22dff163d063e2a52bc8adcae',
            'info_dict': {
                'id': '5706148',
                'ext': 'mp3',
                'duration': 123,
                'title': '"Urban Hippie", de Damien Krisl',
                'description': 'Des Hippies super glam.',
                'upload_date': '20140403',
                'timestamp': 1396551600,
            },
        },
    ]

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url)
        video_id = m.group('id')

        def download_json(internal_id):
            return self._download_json(
                'http://www.rts.ch/a/%s.html?f=json/article' % internal_id,
                video_id)

        all_info = download_json(video_id)

        # video_id extracted out of URL is not always a real id
        if 'video' not in all_info and 'audio' not in all_info:
            page = self._download_webpage(url, video_id)
            internal_id = self._html_search_regex(
                r'<(?:video|audio) data-id="([0-9]+)"', page,
                'internal video id')
            all_info = download_json(internal_id)

        info = all_info['video']['JSONinfo'] if 'video' in all_info else all_info['audio']

        upload_timestamp = parse_iso8601(info.get('broadcast_date'))
        duration = info.get('duration') or info.get('cutout') or info.get('cutduration')
        if isinstance(duration, compat_str):
            duration = parse_duration(duration)
        view_count = info.get('plays')
        thumbnail = unescapeHTML(info.get('preview_image_url'))

        def extract_bitrate(url):
            return int_or_none(self._search_regex(
                r'-([0-9]+)k\.', url, 'bitrate', default=None))

        formats = [{
            'format_id': fid,
            'url': furl,
            'tbr': extract_bitrate(furl),
        } for fid, furl in info['streams'].items()]

        if 'media' in info:
            formats.extend([{
                'format_id': '%s-%sk' % (media['ext'], media['rate']),
                'url': 'http://download-video.rts.ch/%s' % media['url'],
                'tbr': media['rate'] or extract_bitrate(media['url']),
            } for media in info['media'] if media.get('rate')])

        self._sort_formats(formats)

        return {
            'id': video_id,
            'formats': formats,
            'title': info['title'],
            'description': info.get('intro'),
            'duration': duration,
            'view_count': view_count,
            'uploader': info.get('programName'),
            'timestamp': upload_timestamp,
            'thumbnail': thumbnail,
        }
