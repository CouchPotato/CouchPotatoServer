from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import possibleTitles, checkQuality, checkCodec
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.matcher.base import MatcherBase
from caper import Caper

log = CPLog(__name__)


class Matcher(MatcherBase):

    def __init__(self):
        super(Matcher, self).__init__()

        self.caper = Caper()

        addEvent('matcher.parse', self.parse)
        addEvent('matcher.match', self.match)

        addEvent('matcher.flatten_info', self.flattenInfo)
        addEvent('matcher.construct_from_raw', self.constructFromRaw)

        addEvent('matcher.correct_title', self.correctTitle)
        addEvent('matcher.correct_quality', self.correctQuality)

    def parse(self, name, parser='scene'):
        return self.caper.parse(name, parser)

    def match(self, release, media, quality):
        match = fireEvent('matcher.parse', release['name'].lower(), single = True)

        if len(match.chains) < 1:
            log.info2('Wrong: %s, unable to parse release name (no chains)', release['name'])
            return False

        for chain in match.chains:
            if fireEvent('%s.matcher.correct' % media['type'], chain, release, media, quality, single = True):
                return chain

        return False

    def correctTitle(self, chain, media):
        root = fireEvent('library.root', media, single = True)

        if 'show_name' not in chain.info or not len(chain.info['show_name']):
            log.info('Wrong: missing show name in parsed result')
            return False

        # Get the lower-case parsed show name from the chain
        chain_words = [x.lower() for x in chain.info['show_name']]

        # Build a list of possible titles of the media we are searching for
        titles = root['info']['titles']

        # Add year suffix titles (will result in ['<name_one>', '<name_one> <suffix_one>', '<name_two>', ...])
        suffixes = [None, root['info']['year']]

        titles = [
            title + ((' %s' % suffix) if suffix else '')
            for title in titles
            for suffix in suffixes
        ]

        # Check show titles match
        # TODO check xem names
        for title in titles:
            for valid_words in [x.split(' ') for x in possibleTitles(title)]:

                if valid_words == chain_words:
                    return True

        return False

    def correctQuality(self, chain, quality, quality_map):
        log.info('quality: %s', quality['identifier'])
        release_video_info = {}
        for link in chain.info['video']: 
            release_video_info.update(link)
        codec = checkCodec(release_video_info)
        log.info('release_video_info: %s', release_video_info)
        
        sd, hd, r720, r1080, rip, tv, webrip = (False,)*7

        # 720 Resolution
        if checkQuality(release_video_info, 'resolution', ["720p","720i"]):
            hd = True
            r720 = True

        # 1080 resolution
        elif checkQuality(release_video_info, 'resolution', ["1080p","1080i"]):
            hd = True
            r1080 = True

        # SD resolutions
        elif checkQuality(release_video_info, 'resolution', ["480p","480i","576p","576i"]):
            sd = True

        # default to sd for unknown resolution
        else:
            sd = True

        # Sources

        # Disc Rip        
        if checkQuality(release_video_info, 'source', ['dvdrip', 'bdrip', 'brrip', 'bluray', ['blu', 'ray']]):
            rip = True

        # TV Rip
        elif checkQuality(release_video_info, 'source', ['hdtv', 'pdtv', 'ws']):
            tv = True

        # Web Rip
        elif checkQuality(release_video_info, 'source', [['web', 'dl'], 'itunes']):
            webrip = True

        # SDTV
        # checkName( SOURCE (pdtv|hdtv|dsr|tvrip) AND CODEC (xvid|x264)"], all)
        # and not checkName RESOLUTION (["(720|1080)[pi]"], all)
        # and not checkName(["hr.ws.pdtv.x264"], any):
        # 
        # checkName([SOURCE "web.dl|webrip", CODEC "xvid|x264|h.?264"], all)
        # not checkName RESOLUTION (["(720|1080)[pi]"], all): 
        if (tv and codec in ["xvid", "x264"] and not hd) or (webrip and codec in ["xvid", "x264", "h264"] and not hd):
            log.info("this is SDTV!")
            if quality['identifier'] == "sdtv":
                return True
        
        # SDDVD
        # checkName(["(dvdrip|bdrip)(.ws)?.(xvid|divx|x264)"], any) and not checkName(["(720|1080)[pi]"], all):
        elif rip or codec in ["xvid", "divx", "x264"] and not hd:
            log.info("this is SDDVD!")
            if quality['identifier'] == "sddvd":
                log.info('BANG!')
                return True
        
        # HDTV 
        # checkName(["720p", "hdtv", "x264"], all) or checkName(["hr.ws.pdtv.x264"], any) and not checkName(["(1080)[pi]"], all):
        elif r720 and tv or codec == "x264" and not webrip:
            log.info("this is 720 HDTV!")
            if quality['identifier'] == "hdtv":
                log.info('BANG!')
                return True

        # RAW-HDTV
        # checkName(["720p|1080i", "hdtv", "mpeg-?2"], all) or checkName(["1080[pi].hdtv", "h.?264"], all):
        elif (r720 or r1080 and codec in ["mpeg2", ["mpeg", "2"]]) or (r1080 and tv and codec in ["h264", ["h", "264"]]):
            log.info("this is RAW-HDTV!")
            if quality['identifier'] == "raw_hdtv":
                log.info('BANG!')
                return True
        
        # 1080 HDTV
        # checkName(["1080p", "hdtv", "x264"], all):
        elif r1080 and tv and codec == "x264":
            log.info('this is 1080 HDTV!')
            if quality['identifier'] == "hdtv_1080p":
                log.info('BANG!')
                return True
        
        # 720 WEB-DL
        # checkName(["720p", "web.dl|webrip"], all) or checkName(["720p", "itunes", "h.?264"], all):
        elif r720 and webrip:
            log.info('this is 720 WEB-DL!')
            if quality['identifier'] == "webdl_720p":
                log.info('BANG!')
                return True

        # 1080 WEB-DL
        # checkName(["1080p", "web.dl|webrip"], all) or checkName(["1080p", "itunes", "h.?264"], all)
        elif r1080 and webrip:
            log.info('this is 1080 WEB-DL!')
            if quality['identifier'] == "webdl_1080p":
                log.info('BANG!')
                return True

        # 720 BLURAY
        # checkName(["720p", "bluray|hddvd", "x264"], all):
        elif r720 and rip and codec == "x264":
            log.info('this is 720 BluRay!')
            if quality['identifier'] == "bluray_720p":
                log.info('BANG!')
                return True

        # 1080 BLURAY
        # checkName(["1080p", "bluray|hddvd", "x264"], all):
        elif r1080 and rip and codec == "x264":
            log.info('this is 1080 BluRay!')
            if quality['identifier'] == "bluray_1080p":
                log.info('BANG!')
                return True

        else:
            log.info('unknown quality')
            log.info('SD: %s', sd)
            log.info('HD: %s', hd)
            log.info('720: %s', r720)
            log.info('1080: %s', r1080)
            log.info('DiscRip: %s', rip)
            log.info('TVRip: %s', tv)
            log.info('WebRip: %s', webrip)
            log.info('codec: %s', codec)
        return False