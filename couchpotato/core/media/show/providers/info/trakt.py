import urllib

from couchpotato.core.event import addEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.media.show.providers.base import ShowProvider

log = CPLog(__name__)

autoload = 'Trakt'


class Trakt(ShowProvider):
    api_key = 'c043de5ada9d180028c10229d2a3ea5b'
    base_url = 'http://api.trakt.tv/%%s.json/%s' % api_key

    def __init__(self):
        addEvent('info.search', self.search, priority = 1)
        addEvent('show.search', self.search, priority = 1)

    def search(self, q, limit = 12):
        if self.isDisabled():
            return False

        # Check for cached result
        cache_key = 'trakt.cache.search.%s.%s' % (q, limit)
        results = self.getCache(cache_key) or []

        if results:
            return results

        # Search
        log.debug('Searching for show: "%s"', q)
        response = self._request('search/shows', query=q, limit=limit)

        if not response:
            return []

        # Parse search results
        for show in response:
            results.append(self._parseShow(show))

        log.info('Found: %s', [result['titles'][0] + ' (' + str(result.get('year', 0)) + ')' for result in results])

        self.setCache(cache_key, results)
        return results

    def _request(self, action, **kwargs):
        url = self.base_url % action

        if kwargs:
            url += '?' + urllib.urlencode(kwargs)

        return self.getJsonData(url)

    def _parseShow(self, show):
        # Images
        images = show.get('images', {})

        poster = images.get('poster')
        backdrop = images.get('backdrop')

        # Rating
        rating = show.get('ratings', {}).get('percentage')

        # Build show dict
        show_data = {
            'identifiers': {
                'thetvdb': show.get('tvdb_id'),
                'imdb': show.get('imdb_id'),
                'tvrage': show.get('tvrage_id'),
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
            'rating': {
                'trakt': float(rating) / 10
            },
        }

        return dict((k, v) for k, v in show_data.iteritems() if v)
