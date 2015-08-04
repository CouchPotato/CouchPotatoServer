from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.trakt.main import TraktBase
from couchpotato.core.media.show.providers.base import ShowProvider

log = CPLog(__name__)

autoload = 'Trakt'


class Trakt(ShowProvider, TraktBase):

    def __init__(self):
        addEvent('info.search', self.search, priority = 1)
        addEvent('show.search', self.search, priority = 1)

    def search(self, q, limit = 12):
        if self.isDisabled() or not self.conf('enabled', section='shows'):
            log.debug('Not searching for show: %s', q)
            return False

        # Search
        log.debug('Searching for show: "%s"', q)

        response = self.call('search?type=show&query=%s' % (q))

        results = []
        for show in response:
            results.append(self._parseShow(show.get('show')))

        for result in results:
            if 'year' in result:
                log.info('Found: %s', result['titles'][0] + ' (' + str(result.get('year', 0)) + ')')
            else:
                log.info('Found: %s', result['titles'][0])

        return results

    def _parseShow(self, show):
        # Images
        images = show.get('images', {})

        poster = images.get('poster', {}).get('thumb')
        backdrop = images.get('fanart', {}).get('thumb')

        # Build show dict
        show_data = {
            'identifiers': {
                'thetvdb': show.get('ids', {}).get('tvdb'),
                'imdb': show.get('ids', {}).get('imdb'),
                'tvrage': show.get('ids', {}).get('tvrage'),
            },
            'type': 'show',
            'titles': [show.get('title')],
            'images': {
                'poster': [poster] if poster else [],
                'backdrop': [backdrop] if backdrop else [],
                'poster_original': [],
                'backdrop_original': [],
            },
            'year': show.get('year'),
        }

        return dict((k, v) for k, v in show_data.iteritems() if v)
