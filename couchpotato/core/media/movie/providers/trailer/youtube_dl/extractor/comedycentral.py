from __future__ import unicode_literals

import re

from .common import InfoExtractor
from .mtv import MTVServicesInfoExtractor
from ..utils import (
    compat_str,
    compat_urllib_parse,
    ExtractorError,
    float_or_none,
    unified_strdate,
)


class ComedyCentralIE(MTVServicesInfoExtractor):
    _VALID_URL = r'''(?x)https?://(?:www\.)?(comedycentral|cc)\.com/
        (video-clips|episodes|cc-studios|video-collections)
        /(?P<title>.*)'''
    _FEED_URL = 'http://comedycentral.com/feeds/mrss/'

    _TEST = {
        'url': 'http://www.comedycentral.com/video-clips/kllhuv/stand-up-greg-fitzsimmons--uncensored---too-good-of-a-mother',
        'md5': 'c4f48e9eda1b16dd10add0744344b6d8',
        'info_dict': {
            'id': 'cef0cbb3-e776-4bc9-b62e-8016deccb354',
            'ext': 'mp4',
            'title': 'CC:Stand-Up|Greg Fitzsimmons: Life on Stage|Uncensored - Too Good of a Mother',
            'description': 'After a certain point, breastfeeding becomes c**kblocking.',
        },
    }


class ComedyCentralShowsIE(InfoExtractor):
    IE_DESC = 'The Daily Show / The Colbert Report'
    # urls can be abbreviations like :thedailyshow or :colbert
    # urls for episodes like:
    # or urls for clips like: http://www.thedailyshow.com/watch/mon-december-10-2012/any-given-gun-day
    #                     or: http://www.colbertnation.com/the-colbert-report-videos/421667/november-29-2012/moon-shattering-news
    #                     or: http://www.colbertnation.com/the-colbert-report-collections/422008/festival-of-lights/79524
    _VALID_URL = r'''(?x)^(:(?P<shortname>tds|thedailyshow|cr|colbert|colbertnation|colbertreport)
                      |https?://(:www\.)?
                          (?P<showname>thedailyshow|thecolbertreport)\.(?:cc\.)?com/
                         ((?:full-)?episodes/(?:[0-9a-z]{6}/)?(?P<episode>.*)|
                          (?P<clip>
                              (?:(?:guests/[^/]+|videos|video-playlists|special-editions)/[^/]+/(?P<videotitle>[^/?#]+))
                              |(the-colbert-report-(videos|collections)/(?P<clipID>[0-9]+)/[^/]*/(?P<cntitle>.*?))
                              |(watch/(?P<date>[^/]*)/(?P<tdstitle>.*))
                          )|
                          (?P<interview>
                              extended-interviews/(?P<interID>[0-9a-z]+)/(?:playlist_tds_extended_)?(?P<interview_title>.*?)(/.*?)?)))
                     (?:[?#].*|$)'''
    _TEST = {
        'url': 'http://thedailyshow.cc.com/watch/thu-december-13-2012/kristen-stewart',
        'md5': '4e2f5cb088a83cd8cdb7756132f9739d',
        'info_dict': {
            'id': 'ab9ab3e7-5a98-4dbe-8b21-551dc0523d55',
            'ext': 'mp4',
            'upload_date': '20121213',
            'description': 'Kristen Stewart learns to let loose in "On the Road."',
            'uploader': 'thedailyshow',
            'title': 'thedailyshow kristen-stewart part 1',
        }
    }

    _available_formats = ['3500', '2200', '1700', '1200', '750', '400']

    _video_extensions = {
        '3500': 'mp4',
        '2200': 'mp4',
        '1700': 'mp4',
        '1200': 'mp4',
        '750': 'mp4',
        '400': 'mp4',
    }
    _video_dimensions = {
        '3500': (1280, 720),
        '2200': (960, 540),
        '1700': (768, 432),
        '1200': (640, 360),
        '750': (512, 288),
        '400': (384, 216),
    }

    @staticmethod
    def _transform_rtmp_url(rtmp_video_url):
        m = re.match(r'^rtmpe?://.*?/(?P<finalid>gsp\.comedystor/.*)$', rtmp_video_url)
        if not m:
            raise ExtractorError('Cannot transform RTMP url')
        base = 'http://mtvnmobile.vo.llnwd.net/kip0/_pxn=1+_pxI0=Ripod-h264+_pxL0=undefined+_pxM0=+_pxK=18639+_pxE=mp4/44620/mtvnorigin/'
        return base + m.group('finalid')

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url, re.VERBOSE)
        if mobj is None:
            raise ExtractorError('Invalid URL: %s' % url)

        if mobj.group('shortname'):
            if mobj.group('shortname') in ('tds', 'thedailyshow'):
                url = 'http://thedailyshow.cc.com/full-episodes/'
            else:
                url = 'http://thecolbertreport.cc.com/full-episodes/'
            mobj = re.match(self._VALID_URL, url, re.VERBOSE)
            assert mobj is not None

        if mobj.group('clip'):
            if mobj.group('videotitle'):
                epTitle = mobj.group('videotitle')
            elif mobj.group('showname') == 'thedailyshow':
                epTitle = mobj.group('tdstitle')
            else:
                epTitle = mobj.group('cntitle')
            dlNewest = False
        elif mobj.group('interview'):
            epTitle = mobj.group('interview_title')
            dlNewest = False
        else:
            dlNewest = not mobj.group('episode')
            if dlNewest:
                epTitle = mobj.group('showname')
            else:
                epTitle = mobj.group('episode')
        show_name = mobj.group('showname')

        webpage, htmlHandle = self._download_webpage_handle(url, epTitle)
        if dlNewest:
            url = htmlHandle.geturl()
            mobj = re.match(self._VALID_URL, url, re.VERBOSE)
            if mobj is None:
                raise ExtractorError('Invalid redirected URL: ' + url)
            if mobj.group('episode') == '':
                raise ExtractorError('Redirected URL is still not specific: ' + url)
            epTitle = mobj.group('episode').rpartition('/')[-1]

        mMovieParams = re.findall('(?:<param name="movie" value="|var url = ")(http://media.mtvnservices.com/([^"]*(?:episode|video).*?:.*?))"', webpage)
        if len(mMovieParams) == 0:
            # The Colbert Report embeds the information in a without
            # a URL prefix; so extract the alternate reference
            # and then add the URL prefix manually.

            altMovieParams = re.findall('data-mgid="([^"]*(?:episode|video|playlist).*?:.*?)"', webpage)
            if len(altMovieParams) == 0:
                raise ExtractorError('unable to find Flash URL in webpage ' + url)
            else:
                mMovieParams = [("http://media.mtvnservices.com/" + altMovieParams[0], altMovieParams[0])]

        uri = mMovieParams[0][1]
        # Correct cc.com in uri
        uri = re.sub(r'(episode:[^.]+)(\.cc)?\.com', r'\1.cc.com', uri)

        index_url = 'http://%s.cc.com/feeds/mrss?%s' % (show_name, compat_urllib_parse.urlencode({'uri': uri}))
        idoc = self._download_xml(
            index_url, epTitle,
            'Downloading show index', 'Unable to download episode index')

        title = idoc.find('./channel/title').text
        description = idoc.find('./channel/description').text

        entries = []
        item_els = idoc.findall('.//item')
        for part_num, itemEl in enumerate(item_els):
            upload_date = unified_strdate(itemEl.findall('./pubDate')[0].text)
            thumbnail = itemEl.find('.//{http://search.yahoo.com/mrss/}thumbnail').attrib.get('url')

            content = itemEl.find('.//{http://search.yahoo.com/mrss/}content')
            duration = float_or_none(content.attrib.get('duration'))
            mediagen_url = content.attrib['url']
            guid = itemEl.find('./guid').text.rpartition(':')[-1]

            cdoc = self._download_xml(
                mediagen_url, epTitle,
                'Downloading configuration for segment %d / %d' % (part_num + 1, len(item_els)))

            turls = []
            for rendition in cdoc.findall('.//rendition'):
                finfo = (rendition.attrib['bitrate'], rendition.findall('./src')[0].text)
                turls.append(finfo)

            formats = []
            for format, rtmp_video_url in turls:
                w, h = self._video_dimensions.get(format, (None, None))
                formats.append({
                    'format_id': 'vhttp-%s' % format,
                    'url': self._transform_rtmp_url(rtmp_video_url),
                    'ext': self._video_extensions.get(format, 'mp4'),
                    'height': h,
                    'width': w,
                })
                formats.append({
                    'format_id': 'rtmp-%s' % format,
                    'url': rtmp_video_url,
                    'ext': self._video_extensions.get(format, 'mp4'),
                    'height': h,
                    'width': w,
                })
                self._sort_formats(formats)

            virtual_id = show_name + ' ' + epTitle + ' part ' + compat_str(part_num + 1)
            entries.append({
                'id': guid,
                'title': virtual_id,
                'formats': formats,
                'uploader': show_name,
                'upload_date': upload_date,
                'duration': duration,
                'thumbnail': thumbnail,
                'description': description,
            })

        return {
            '_type': 'playlist',
            'entries': entries,
            'title': show_name + ' ' + title,
            'description': description,
        }
