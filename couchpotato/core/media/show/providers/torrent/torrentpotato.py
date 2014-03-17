from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.logger import CPLog
from couchpotato.core.event import fireEvent
from couchpotato.core.media._base.providers.base import MultiProvider
from couchpotato.core.media.show.providers.base import SeasonProvider, EpisodeProvider
from couchpotato.core.media._base.providers.torrent.torrentpotato import Base

log = CPLog(__name__)

autoload = 'TorrentPotato'


class TorrentPotato(MultiProvider):

    def getTypes(self):
        return [Season, Episode]


class Season(SeasonProvider, Base):

    def buildUrl(self, media, host):
        arguments = tryUrlencode({
            'user': host['name'],
            'passkey': host['pass_key'],
            'search': fireEvent('media.search_query', media, single = True)
        })
        return '%s?%s' % (host['host'], arguments)


class Episode(EpisodeProvider, Base):

    def buildUrl(self, media, host):
        arguments = tryUrlencode({
            'user': host['name'],
            'passkey': host['pass_key'],
            'search': fireEvent('media.search_query', media, single = True)
        })
        return '%s?%s' % (host['host'], arguments)
