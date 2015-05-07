from couchpotato import fireEvent, CPLog
from couchpotato.core.media.show.matcher.base import Base

log = CPLog(__name__)


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
