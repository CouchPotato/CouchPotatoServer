from couchpotato import fireEvent, CPLog, tryInt
from couchpotato.core.event import addEvent
from couchpotato.core.media._base.matcher.base import MatcherBase

log = CPLog(__name__)


class Base(MatcherBase):
    def __init__(self):
        super(Base, self).__init__()

        addEvent('%s.matcher.correct_identifier' % self.type, self.correctIdentifier)

    def correct(self, chain, release, media, quality):
        log.info("Checking if '%s' is valid", release['name'])
        log.info2('Release parsed as: %s', chain.info)

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
