from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.encoding import ss
from couchpotato.core.helpers.variable import splitString, md5
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Movie
from couchpotato.environment import Env
from sqlalchemy.sql.expression import or_

class Suggestion(Plugin):

    def __init__(self):

        addApiView('suggestion.view', self.suggestView)
        addApiView('suggestion.ignore', self.ignoreView)

    def suggestView(self, **kwargs):

        movies = splitString(kwargs.get('movies', ''))
        ignored = splitString(kwargs.get('ignored', ''))
        limit = kwargs.get('limit', 6)

        if not movies or len(movies) == 0:
            db = get_session()
            active_movies = db.query(Movie) \
                .filter(or_(*[Movie.status.has(identifier = s) for s in ['active', 'done']])).all()
            movies = [x.library.identifier for x in active_movies]

        if not ignored or len(ignored) == 0:
            ignored = splitString(Env.prop('suggest_ignore', default = ''))

        cached_suggestion = self.getCache('suggestion_cached')
        if cached_suggestion:
            suggestions = cached_suggestion
        else:
            suggestions = fireEvent('movie.suggest', movies = movies, ignore = ignored, single = True)
            self.setCache(md5(ss('suggestion_cached')), suggestions, timeout = 6048000) # Cache for 10 weeks

        return {
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions[:limit]
        }

    def ignoreView(self, imdb = None, limit = 6, remove_only = False, **kwargs):

        ignored = splitString(Env.prop('suggest_ignore', default = ''))

        if imdb:
            if not remove_only:
                ignored.append(imdb)
                Env.prop('suggest_ignore', ','.join(set(ignored)))

            new_suggestions = self.updateSuggestionCache(ignore_imdb = imdb, limit = limit, ignored = ignored)

        return {
            'result': True,
            'ignore_count': len(ignored),
            'suggestions': new_suggestions[limit - 1:limit]
        }

    def updateSuggestionCache(self, ignore_imdb = None, limit = 6, ignored = None):

        # Combine with previous suggestion_cache
        cached_suggestion = self.getCache('suggestion_cached')
        new_suggestions = []
        ignored = [] if not ignored else ignored

        if ignore_imdb:
            for cs in cached_suggestion:
                if cs.get('imdb') != ignore_imdb:
                    new_suggestions.append(cs)

        # Get new results and add them
        if len(new_suggestions) - 1 < limit:

            db = get_session()
            active_movies = db.query(Movie) \
                .filter(or_(*[Movie.status.has(identifier = s) for s in ['active', 'done']])).all()
            movies = [x.library.identifier for x in active_movies]

            ignored.extend([x.get('imdb') for x in cached_suggestion])
            suggestions = fireEvent('movie.suggest', movies = movies, ignore = list(set(ignored)), single = True)

            if suggestions:
                new_suggestions.extend(suggestions)

        self.setCache(md5(ss('suggestion_cached')), new_suggestions, timeout = 6048000)

        return new_suggestions
