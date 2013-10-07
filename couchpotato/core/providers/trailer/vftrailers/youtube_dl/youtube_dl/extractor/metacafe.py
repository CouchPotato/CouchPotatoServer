import re
import socket

from .common import InfoExtractor
from ..utils import (
    compat_http_client,
    compat_parse_qs,
    compat_urllib_error,
    compat_urllib_parse,
    compat_urllib_request,
    compat_str,
    determine_ext,
    ExtractorError,
)

class MetacafeIE(InfoExtractor):
    """Information Extractor for metacafe.com."""

    _VALID_URL = r'(?:http://)?(?:www\.)?metacafe\.com/watch/([^/]+)/([^/]+)/.*'
    _DISCLAIMER = 'http://www.metacafe.com/family_filter/'
    _FILTER_POST = 'http://www.metacafe.com/f/index.php?inputType=filter&controllerGroup=user'
    IE_NAME = u'metacafe'
    _TESTS = [{
        u"add_ie": ["Youtube"],
        u"url":  u"http://metacafe.com/watch/yt-_aUehQsCQtM/the_electric_company_short_i_pbs_kids_go/",
        u"file":  u"_aUehQsCQtM.flv",
        u"info_dict": {
            u"upload_date": u"20090102",
            u"title": u"The Electric Company | \"Short I\" | PBS KIDS GO!",
            u"description": u"md5:2439a8ef6d5a70e380c22f5ad323e5a8",
            u"uploader": u"PBS",
            u"uploader_id": u"PBS"
        }
    },
    {
        u"url": u"http://www.metacafe.com/watch/an-dVVXnuY7Jh77J/the_andromeda_strain_1971_stop_the_bomb_part_3/",
        u"file": u"an-dVVXnuY7Jh77J.mp4",
        u"info_dict": {
            u"title": u"The Andromeda Strain (1971): Stop the Bomb Part 3",
            u"uploader": u"anyclip",
            u"description": u"md5:38c711dd98f5bb87acf973d573442e67"
        }
    }]


    def report_disclaimer(self):
        """Report disclaimer retrieval."""
        self.to_screen(u'Retrieving disclaimer')

    def _real_initialize(self):
        # Retrieve disclaimer
        request = compat_urllib_request.Request(self._DISCLAIMER)
        try:
            self.report_disclaimer()
            compat_urllib_request.urlopen(request).read()
        except (compat_urllib_error.URLError, compat_http_client.HTTPException, socket.error) as err:
            raise ExtractorError(u'Unable to retrieve disclaimer: %s' % compat_str(err))

        # Confirm age
        disclaimer_form = {
            'filters': '0',
            'submit': "Continue - I'm over 18",
            }
        request = compat_urllib_request.Request(self._FILTER_POST, compat_urllib_parse.urlencode(disclaimer_form))
        try:
            self.report_age_confirmation()
            compat_urllib_request.urlopen(request).read()
        except (compat_urllib_error.URLError, compat_http_client.HTTPException, socket.error) as err:
            raise ExtractorError(u'Unable to confirm age: %s' % compat_str(err))

    def _real_extract(self, url):
        # Extract id and simplified title from URL
        mobj = re.match(self._VALID_URL, url)
        if mobj is None:
            raise ExtractorError(u'Invalid URL: %s' % url)

        video_id = mobj.group(1)

        # Check if video comes from YouTube
        mobj2 = re.match(r'^yt-(.*)$', video_id)
        if mobj2 is not None:
            return [self.url_result('http://www.youtube.com/watch?v=%s' % mobj2.group(1), 'Youtube')]

        # Retrieve video webpage to extract further information
        req = compat_urllib_request.Request('http://www.metacafe.com/watch/%s/' % video_id)
        req.headers['Cookie'] = 'flashVersion=0;'
        webpage = self._download_webpage(req, video_id)

        # Extract URL, uploader and title from webpage
        self.report_extraction(video_id)
        mobj = re.search(r'(?m)&mediaURL=([^&]+)', webpage)
        if mobj is not None:
            mediaURL = compat_urllib_parse.unquote(mobj.group(1))
            video_ext = mediaURL[-3:]

            # Extract gdaKey if available
            mobj = re.search(r'(?m)&gdaKey=(.*?)&', webpage)
            if mobj is None:
                video_url = mediaURL
            else:
                gdaKey = mobj.group(1)
                video_url = '%s?__gda__=%s' % (mediaURL, gdaKey)
        else:
            mobj = re.search(r'<video src="([^"]+)"', webpage)
            if mobj:
                video_url = mobj.group(1)
                video_ext = 'mp4'
            else:
                mobj = re.search(r' name="flashvars" value="(.*?)"', webpage)
                if mobj is None:
                    raise ExtractorError(u'Unable to extract media URL')
                vardict = compat_parse_qs(mobj.group(1))
                if 'mediaData' not in vardict:
                    raise ExtractorError(u'Unable to extract media URL')
                mobj = re.search(r'"mediaURL":"(?P<mediaURL>http.*?)",(.*?)"key":"(?P<key>.*?)"', vardict['mediaData'][0])
                if mobj is None:
                    raise ExtractorError(u'Unable to extract media URL')
                mediaURL = mobj.group('mediaURL').replace('\\/', '/')
                video_url = '%s?__gda__=%s' % (mediaURL, mobj.group('key'))
                video_ext = determine_ext(video_url)

        video_title = self._html_search_regex(r'(?im)<title>(.*) - Video</title>', webpage, u'title')
        description = self._og_search_description(webpage)
        video_uploader = self._html_search_regex(
                r'submitter=(.*?);|googletag\.pubads\(\)\.setTargeting\("(?:channel|submiter)","([^"]+)"\);',
                webpage, u'uploader nickname', fatal=False)

        return {
            '_type':    'video',
            'id':       video_id,
            'url':      video_url,
            'description': description,
            'uploader': video_uploader,
            'upload_date':  None,
            'title':    video_title,
            'ext':      video_ext,
        }
