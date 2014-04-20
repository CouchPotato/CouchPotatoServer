import re
import json

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    xpath_with_ns,
)

_x = lambda p: xpath_with_ns(p, {'smil': 'http://www.w3.org/2005/SMIL21/Language'})


class ThePlatformIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        (?:https?://(?:link|player)\.theplatform\.com/[sp]/[^/]+/
           (?P<config>(?:[^/\?]+/(?:swf|config)|onsite)/select/)?
         |theplatform:)(?P<id>[^/\?&]+)'''

    _TEST = {
        # from http://www.metacafe.com/watch/cb-e9I_cZgTgIPd/blackberrys_big_bold_z30/
        u'url': u'http://link.theplatform.com/s/dJ5BDC/e9I_cZgTgIPd/meta.smil?format=smil&Tracking=true&mbr=true',
        u'info_dict': {
            u'id': u'e9I_cZgTgIPd',
            u'ext': u'flv',
            u'title': u'Blackberry\'s big, bold Z30',
            u'description': u'The Z30 is Blackberry\'s biggest, baddest mobile messaging device yet.',
            u'duration': 247,
        },
        u'params': {
            # rtmp download
            u'skip_download': True,
        },
    }

    def _get_info(self, video_id, smil_url):
        meta = self._download_xml(smil_url, video_id)

        try:
            error_msg = next(
                n.attrib['abstract']
                for n in meta.findall(_x('.//smil:ref'))
                if n.attrib.get('title') == u'Geographic Restriction')
        except StopIteration:
            pass
        else:
            raise ExtractorError(error_msg, expected=True)

        info_url = 'http://link.theplatform.com/s/dJ5BDC/{0}?format=preview'.format(video_id)
        info_json = self._download_webpage(info_url, video_id)
        info = json.loads(info_json)

        head = meta.find(_x('smil:head'))
        body = meta.find(_x('smil:body'))

        f4m_node = body.find(_x('smil:seq/smil:video'))
        if f4m_node is not None:
            f4m_url = f4m_node.attrib['src']
            if 'manifest.f4m?' not in f4m_url:
                f4m_url += '?'
            # the parameters are from syfy.com, other sites may use others,
            # they also work for nbc.com
            f4m_url += '&g=UXWGVKRWHFSP&hdcore=3.0.3'
            formats = [{
                'ext': 'flv',
                'url': f4m_url,
            }]
        else:
            base_url = head.find(_x('smil:meta')).attrib['base']
            switch = body.find(_x('smil:switch'))
            formats = []
            for f in switch.findall(_x('smil:video')):
                attr = f.attrib
                width = int(attr['width'])
                height = int(attr['height'])
                vbr = int(attr['system-bitrate']) // 1000
                format_id = '%dx%d_%dk' % (width, height, vbr)
                formats.append({
                    'format_id': format_id,
                    'url': base_url,
                    'play_path': 'mp4:' + attr['src'],
                    'ext': 'flv',
                    'width': width,
                    'height': height,
                    'vbr': vbr,
                })
            self._sort_formats(formats)

        return {
            'id': video_id,
            'title': info['title'],
            'formats': formats,
            'description': info['description'],
            'thumbnail': info['defaultThumbnailUrl'],
            'duration': info['duration']//1000,
        }
        
    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        video_id = mobj.group('id')
        if mobj.group('config'):
            config_url = url+ '&form=json'
            config_url = config_url.replace('swf/', 'config/')
            config_url = config_url.replace('onsite/', 'onsite/config/')
            config_json = self._download_webpage(config_url, video_id, u'Downloading config')
            config = json.loads(config_json)
            smil_url = config['releaseUrl'] + '&format=SMIL&formats=MPEG4&manifest=f4m'
        else:
            smil_url = ('http://link.theplatform.com/s/dJ5BDC/{0}/meta.smil?'
                'format=smil&mbr=true'.format(video_id))
        return self._get_info(video_id, smil_url)
