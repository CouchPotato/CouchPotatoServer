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

    def correctQuality(self, chain, quality):
        log.info('quality: %s', quality['identifier'])
        release_video_info = {}
        for link in chain.info['video']: 
            release_video_info.update(link)
        codec = checkCodec(release_video_info)
        log.info('release_video_info: %s', release_video_info)
        
        hd, interlaced, pdtv, r720, r1080, rip, sd, tv, webrip = (False,) * 9

        # 720 Resolution
        if checkQuality(release_video_info, 'resolution', ['720i', '720p']):
            hd = True
            r720 = True

        # 1080 resolution
        elif checkQuality(release_video_info, 'resolution', ['1080i', '1080p']):
            hd = True
            r1080 = True

        # SD resolutions
        elif checkQuality(release_video_info, 'resolution', ['480i', '480p', '576i', '576p']):
            sd = True

        # default to sd for unknown resolution
        else:
            sd = True
        
        # check if interlaced
        if checkQuality(release_video_info, 'resolution', ['480i', '576i', '720i', '1080i']):
            interlaced = True
        
        # Sources
        # Disc Rip        
        if checkQuality(release_video_info, 'source', ['dvdrip', 'bdrip', 'brrip', 'bluray', 'hddvd', ['blu', 'ray'], ['hd', 'dvd']]):
            rip = True

        # TV Rip
        elif checkQuality(release_video_info, 'source', ['dsr', 'hdtv', 'sdtv', 'tvrip']):
            tv = True

        # Web Rip
        elif checkQuality(release_video_info, 'source', [['web', 'dl'], 'itunes']):
            webrip = True

        if checkQuality(release_video_info, 'source', ['pdtv']):
            pdtv = True

        # Temporary, remove the following line when finished:
        log.info('SD:%s HD: %s, interlaced: %s, pdtv: %s, r720: %s, r1080: %s, rip %s, tv %s, webrip: %s', (sd, hd, interlaced, pdtv, r720, r1080, rip, tv, webrip))

        # sdtv
        if tv and (codec in ['h264', ['h', '264'], 'xvid', 'x264']) and not hd:
            log.info('sdtv')
            if quality['identifier'] == 'sdtv':
                return True

        elif tv and (codec in ['xvid', 'x264']) and not hd and not pdtv:
            log.info('sdtv2')
            if quality['identifier'] == 'sdtv':
                return True

        # sd_dvd
        elif (rip or (codec in ['xvid', 'divx', 'x264'])) and not hd:
            log.info('sd_dvd')
            if quality['identifier'] == 'sd_dvd':
                return True
        
        # hdtv
        elif r720 and tv and (codec == 'x264') and not webrip and not pdtv:
            log.info('hdtv')
            if quality['identifier'] == 'hdtv':
                return True

        # raw_hdtv
        elif ((r720 or (r1080 and interlaced)) and (codec in ['mpeg2', ['mpeg', '2']])) or (r1080 and tv and codec in ['h264', ['h', '264']]):
            log.info('raw_hdtv')
            if quality['identifier'] == 'raw_hdtv':
                return True
        
        # hdtv_1080p
        elif r1080 and not interlaced and tv and (codec == 'x264'):
            log.info('hdtv_1080p')
            if quality['identifier'] == 'hdtv_1080p':
                return True
        
        # webdl_720p
        elif r720 and webrip and not interlaced:
            log.info('webdl_720p')
            if quality['identifier'] == 'webdl_720p':
                return True

        # webdl_1080p
        elif r1080 and webrip and not interlaced:
            log.info('webdl_1080p')
            if quality['identifier'] == 'webdl_1080p':
                return True

        # bluray_720p
        elif r720 and rip and not interlaced:
            log.info('bluray_720p')
            if quality['identifier'] == 'bluray_720p':
                return True

        # bluray_1080p
        elif r1080 and rip and not interlaced:
            log.info('bluray_1080p')
            if quality['identifier'] == 'bluray_1080p':
                return True

        else:
            log.info('unknown quality')
        return False