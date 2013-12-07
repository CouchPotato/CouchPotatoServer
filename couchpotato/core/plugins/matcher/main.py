from caper import Caper
from couchpotato import CPLog, tryInt
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import possibleTitles, dictIsSubset
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class Matcher(Plugin):
    def __init__(self):
        self.caper = Caper()

        addEvent('matcher.parse', self.parse)
        addEvent('matcher.best', self.best)

        addEvent('matcher.correct_title', self.correctTitle)
        addEvent('matcher.correct_identifier', self.correctIdentifier)
        addEvent('matcher.correct_quality', self.correctQuality)

    def parse(self, release):
        return self.caper.parse(release['name'])

    def best(self, release, media, quality):
        match = fireEvent('matcher.parse', release, single = True)

        if len(match.chains) < 1:
            log.info2('Wrong: %s, unable to parse release name (no chains)', release['name'])
            return False

        for chain in match.chains:
            if fireEvent('searcher.correct_match', chain, release, media, quality, single = True):
                return chain

        return False

    def flattenInfo(self, info):
        flat_info = {}

        for match in info:
            for key, value in match.items():
                if key not in flat_info:
                    flat_info[key] = []

                flat_info[key].append(value)

        return flat_info

    def simplifyValue(self, value):
        if not value:
            return value

        if isinstance(value, basestring):
            return simplifyString(value)

        if isinstance(value, list):
            return [self.simplifyValue(x) for x in value]

        raise ValueError("Unsupported value type")

    def chainMatch(self, chain, group, tags):
        info = self.flattenInfo(chain.info[group])

        found_tags = []
        for tag, accepted in tags.items():
            values = [self.simplifyValue(x) for x in info.get(tag, [None])]

            if any([val in accepted for val in values]):
                found_tags.append(tag)

        log.debug('tags found: %s, required: %s' % (found_tags, tags.keys()))

        if set(tags.keys()) == set(found_tags):
            return True

        return all([key in found_tags for key, value in tags.items()])

    def correctIdentifier(self, chain, media):
        required_id = fireEvent('library.identifier', media['library'], single = True)

        if 'identifier' not in chain.info:
            return False

        # TODO could be handled better?
        if len(chain.info['identifier']) != 1:
            return False
        identifier = chain.info['identifier'][0]

        # TODO air by date episodes

        # TODO this should support identifiers with characters 'a', 'b', etc..
        for k, v in identifier.items():
            identifier[k] = tryInt(v, None)

        if any([x in identifier for x in ['episode_from', 'episode_to']]):
            log.info2('Wrong: releases with identifier ranges are not supported yet')
            return False

        # 'episode' is required in identifier for subset matching
        if 'episode' not in identifier:
            identifier['episode'] = None

        if not dictIsSubset(required_id, identifier):
            log.info2('Wrong: required identifier %s does not match release identifier %s', (str(required_id), str(identifier)))
            return False

        return True

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
