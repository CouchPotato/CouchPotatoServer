from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.matcher.episode import Episode
from couchpotato.core.media.show.matcher.season import Season


class ShowMatcher(MultiProvider):

    def getTypes(self):
        return [Season, Episode]
