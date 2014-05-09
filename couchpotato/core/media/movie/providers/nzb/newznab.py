from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.newznab import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'Newznab'


class Newznab(MovieProvider, Base):

    def buildUrl(self, media, host):

        query = tryUrlencode({
            't': 'movie',
            'imdbid': getIdentifier(media).replace('tt', ''),
            'apikey': host['api_key'],
            'extended': 1
        })

        if len(host.get('custom_tag', '')) > 0:
            query = '%s&%s' % (query, host.get('custom_tag'))

        return query
