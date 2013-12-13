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
        # Flatten dictionary of matches (chain info)
        if isinstance(info, dict):
            return dict([(key, self.flattenInfo(value)) for key, value in info.items()])

        # Flatten matches
        result = None

        for match in info:
            if isinstance(match, dict):
                if result is None:
                    result = {}

                for key, value in match.items():
                    if key not in result:
                        result[key] = []

                    result[key].append(value)
            else:
                if result is None:
                    result = []

                result.append(match)

        return result

    def constructFromRaw(self, match):
        if not match:
            return None

        parts = [
            ''.join([
                y for y in x[1:] if y
            ]) for x in match
        ]

        return ''.join(parts)[:-1].strip()

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
