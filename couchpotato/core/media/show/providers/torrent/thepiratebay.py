from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.thepiratebay import Base

log = CPLog(__name__)

autoload = 'ThePirateBay'


class ThePirateBay(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    cat_ids = [
        ([208], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([205], ['hdtv_sd'])
    ]

    def buildUrl(self, media, page, cats):
        return (
            tryUrlencode('"%s"' % fireEvent('media.search_query', media, single = True)),
            page,
            ','.join(str(x) for x in cats)
        )


class Episode(EpisodeProvider, Base):

    cat_ids = [
        ([208], ['hdtv_720p', 'webdl_720p', 'webdl_1080p']),
        ([205], ['hdtv_sd'])
    ]

    def buildUrl(self, media, page, cats):
        return (
            tryUrlencode('"%s"' % fireEvent('media.search_query', media, single = True)),
            page,
            ','.join(str(x) for x in cats)
        )
