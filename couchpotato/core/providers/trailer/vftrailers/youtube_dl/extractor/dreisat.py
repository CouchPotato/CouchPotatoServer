# coding: utf-8

import re
import xml.etree.ElementTree

from .common import InfoExtractor
from ..utils import (
    determine_ext,
    unified_strdate,
)


class DreiSatIE(InfoExtractor):
    IE_NAME = '3sat'
    _VALID_URL = r'(?:http://)?(?:www\.)?3sat.de/mediathek/index.php\?(?:(?:mode|display)=[^&]+&)*obj=(?P<id>[0-9]+)$'
    _TEST = {
        u"url": u"http://www.3sat.de/mediathek/index.php?obj=36983",
        u'file': u'36983.webm',
        u'md5': u'57c97d0469d71cf874f6815aa2b7c944',
        u'info_dict': {
            u"title": u"Kaffeeland Schweiz",
            u"description": u"Über 80 Kaffeeröstereien liefern in der Schweiz das Getränk, in das das Land so vernarrt ist: Mehr als 1000 Tassen trinkt ein Schweizer pro Jahr. SCHWEIZWEIT nimmt die Kaffeekultur unter die...", 
            u"uploader": u"3sat",
            u"upload_date": u"20130622"
        }
    }


    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        details_url = 'http://www.3sat.de/mediathek/xmlservice/web/beitragsDetails?ak=web&id=%s' % video_id
        details_xml = self._download_webpage(details_url, video_id, note=u'Downloading video details')
        details_doc = xml.etree.ElementTree.fromstring(details_xml.encode('utf-8'))

        thumbnail_els = details_doc.findall('.//teaserimage')
        thumbnails = [{
            'width': te.attrib['key'].partition('x')[0],
            'height': te.attrib['key'].partition('x')[2],
            'url': te.text,
        } for te in thumbnail_els]

        information_el = details_doc.find('.//information')
        video_title = information_el.find('./title').text
        video_description = information_el.find('./detail').text

        details_el = details_doc.find('.//details')
        video_uploader = details_el.find('./channel').text
        upload_date = unified_strdate(details_el.find('./airtime').text)

        format_els = details_doc.findall('.//formitaet')
        formats = [{
            'format_id': fe.attrib['basetype'],
            'width': int(fe.find('./width').text),
            'height': int(fe.find('./height').text),
            'url': fe.find('./url').text,
            'ext': determine_ext(fe.find('./url').text),
            'filesize': int(fe.find('./filesize').text),
            'video_bitrate': int(fe.find('./videoBitrate').text),
            '3sat_qualityname': fe.find('./quality').text,
        } for fe in format_els
            if not fe.find('./url').text.startswith('http://www.metafilegenerator.de/')]

        def _sortkey(format):
            qidx = ['low', 'med', 'high', 'veryhigh'].index(format['3sat_qualityname'])
            prefer_http = 1 if 'rtmp' in format['url'] else 0
            return (qidx, prefer_http, format['video_bitrate'])
        formats.sort(key=_sortkey)

        info = {
            '_type': 'video',
            'id': video_id,
            'title': video_title,
            'formats': formats,
            'description': video_description,
            'thumbnails': thumbnails,
            'thumbnail': thumbnails[-1]['url'],
            'uploader': video_uploader,
            'upload_date': upload_date,
        }

        # TODO: Remove when #980 has been merged
        info.update(formats[-1])

        return info
