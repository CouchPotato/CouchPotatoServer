from couchpotato.core.event import addEvent
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin

log = CPLog(__name__)


class MatcherBase(Plugin):
    type = None

    def __init__(self):
        if self.type:
            addEvent('%s.matcher.correct' % self.type, self.correct)

    def correct(self, chain, release, media, quality):
        raise NotImplementedError()

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
