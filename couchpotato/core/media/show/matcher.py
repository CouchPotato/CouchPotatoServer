from couchpotato import CPLog
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.media._base.matcher.base import MatcherBase
from couchpotato.core.media._base.providers.base import MultiProvider

log = CPLog(__name__)

autoload = 'ShowMatcher'


class ShowMatcher(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Base(MatcherBase):

    def __init__(self):
        super(Base, self).__init__()

        addEvent('%s.matcher.correct_identifier' % self.type, self.correctIdentifier)

    def correct(self, chain, release, media, quality):
        log.info("Checking if '%s' is valid", release['name'])
        log.info2('Release parsed as: %s', chain.info)

        if not fireEvent('matcher.correct_quality', chain, quality, single = True):
            log.info('Wrong: %s, quality does not match', release['name'])
            return False

        if not fireEvent('%s.matcher.correct_identifier' % self.type, chain, media):
            log.info('Wrong: %s, identifier does not match', release['name'])
            return False

        if not fireEvent('matcher.correct_title', chain, media):
            log.info("Wrong: '%s', undetermined naming.", (' '.join(chain.info['show_name'])))
            return False

        return True

    def correctIdentifier(self, chain, media):
        raise NotImplementedError()

    def getChainIdentifier(self, chain):
        if 'identifier' not in chain.info:
            return None

        identifier = self.flattenInfo(chain.info['identifier'])

        # Try cast values to integers
        for key, value in identifier.items():
            if isinstance(value, list):
                if len(value) <= 1:
                    value = value[0]
                else:
                    log.warning('Wrong: identifier contains multiple season or episode values, unsupported')
                    return None

            identifier[key] = tryInt(value, value)

        return identifier


class Episode(Base):
    type = 'show.episode'

    def correctIdentifier(self, chain, media):
        identifier = self.getChainIdentifier(chain)
        if not identifier:
            log.info2('Wrong: release identifier is not valid (unsupported or missing identifier)')
            return False

        # TODO - Parse episode ranges from identifier to determine if they are multi-part episodes
        if any([x in identifier for x in ['episode_from', 'episode_to']]):
            log.info2('Wrong: releases with identifier ranges are not supported yet')
            return False

        required = fireEvent('library.identifier', media, single = True)

        # TODO - Support air by date episodes
        # TODO - Support episode parts

        if identifier != required:
            log.info2('Wrong: required identifier (%s) does not match release identifier (%s)', (required, identifier))
            return False

        return True


class Season(Base):
    type = 'show.season'

    def correctIdentifier(self, chain, media):
        identifier = self.getChainIdentifier(chain)
        if not identifier:
            log.info2('Wrong: release identifier is not valid (unsupported or missing identifier)')
            return False

        # TODO - Parse episode ranges from identifier to determine if they are season packs
        if any([x in identifier for x in ['episode_from', 'episode_to']]):
            log.info2('Wrong: releases with identifier ranges are not supported yet')
            return False

        required = fireEvent('library.identifier', media, single = True)

        if identifier != required:
            log.info2('Wrong: required identifier (%s) does not match release identifier (%s)', (required, identifier))
            return False

        return True
