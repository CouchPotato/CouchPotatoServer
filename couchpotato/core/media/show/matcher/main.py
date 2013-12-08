from couchpotato import CPLog
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import dictIsSubset, tryInt, toIterable
from couchpotato.core.media._base.matcher.base import MatcherBase

log = CPLog(__name__)


class ShowMatcher(MatcherBase):

    type = ['show', 'season', 'episode']

    # TODO come back to this later, think this could be handled better, this is starting to get out of hand....
    quality_map = {
        'bluray_1080p': {'resolution': ['1080p'], 'source': ['bluray']},
        'bluray_720p': {'resolution': ['720p'], 'source': ['bluray']},

        'bdrip_1080p': {'resolution': ['1080p'], 'source': ['BDRip']},
        'bdrip_720p': {'resolution': ['720p'], 'source': ['BDRip']},

        'brrip_1080p': {'resolution': ['1080p'], 'source': ['BRRip']},
        'brrip_720p': {'resolution': ['720p'], 'source': ['BRRip']},

        'webdl_1080p': {'resolution': ['1080p'], 'source': ['webdl', ['web', 'dl']]},
        'webdl_720p': {'resolution': ['720p'], 'source': ['webdl', ['web', 'dl']]},
        'webdl_480p': {'resolution': ['480p'], 'source': ['webdl', ['web', 'dl']]},

        'hdtv_720p': {'resolution': ['720p'], 'source': ['hdtv']},
        'hdtv_sd': {'resolution': ['480p', None], 'source': ['hdtv']},
    }

    def __init__(self):
        super(ShowMatcher, self).__init__()

        for type in toIterable(self.type):
            addEvent('%s.matcher.correct' % type, self.correct)
            addEvent('%s.matcher.correct_identifier' % type, self.correctIdentifier)

    def correct(self, chain, release, media, quality):
        log.info("Checking if '%s' is valid", release['name'])
        log.info2('Release parsed as: %s', chain.info)

        if not fireEvent('matcher.correct_quality', chain, quality, self.quality_map, single = True):
            log.info('Wrong: %s, quality does not match', release['name'])
            return False

        if not fireEvent('show.matcher.correct_identifier', chain, media):
            log.info('Wrong: %s, identifier does not match', release['name'])
            return False

        if not fireEvent('matcher.correct_title', chain, media):
            log.info("Wrong: '%s', undetermined naming.", (' '.join(chain.info['show_name'])))
            return False

        return True

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
