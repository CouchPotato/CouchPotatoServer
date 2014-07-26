from couchpotato.core.media._base.providers.info.base import BaseInfoProvider


class ShowProvider(BaseInfoProvider):
    type = 'show'


class SeasonProvider(BaseInfoProvider):
    type = 'show.season'


class EpisodeProvider(BaseInfoProvider):
    type = 'show.episode'
