from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import possibleTitles
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
        match = fireEvent('matcher.parse', release['name'], single = True)

        if len(match.chains) < 1:
            log.info2('Wrong: %s, unable to parse release name (no chains)', release['name'])
            return False

        for chain in match.chains:
            if fireEvent('%s.matcher.correct' % media['type'], chain, release, media, quality, single = True):
                return chain

        return False

    def correctTitle(self, chain, media):
        root_library = media['library']['root_library']

        if 'show_name' not in chain.info or not len(chain.info['show_name']):
            log.info('Wrong: missing show name in parsed result')
            return False

        # Get the lower-case parsed show name from the chain
        chain_words = [x.lower() for x in chain.info['show_name']]

        # Build a list of possible titles of the media we are searching for
        titles = root_library['info']['titles']

        # Add year suffix titles (will result in ['<name_one>', '<name_one> <suffix_one>', '<name_two>', ...])
        suffixes = [None, root_library['info']['year']]

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
        if quality['identifier'] not in quality_map:
            log.info2('Wrong: unknown preferred quality %s', quality['identifier'])
            return False

        if 'video' not in chain.info:
            log.info2('Wrong: no video tags found')
            return False

        video_tags = quality_map[quality['identifier']]

        if not self.chainMatch(chain, 'video', video_tags):
            log.info2('Wrong: %s tags not in chain', video_tags)
            return False

        return True
