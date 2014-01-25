from couchpotato import get_session
from couchpotato.api import addApiView
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import splitString, removeDuplicate
from couchpotato.core.plugins.base import Plugin
from couchpotato.core.settings.model import Media, Library
from couchpotato.environment import Env
from sqlalchemy.orm import joinedload_all
from sqlalchemy.sql.expression import or_


class Suggestion(Plugin):

    def __init__(self):

        addApiView('suggestion.view', self.suggestView)
        addApiView('suggestion.ignore', self.ignoreView)

    def suggestView(self, limit = 6, **kwargs):

        movies = splitString(kwargs.get('movies', ''))
        ignored = splitString(kwargs.get('ignored', ''))
        seen = splitString(kwargs.get('seen', ''))

        cached_suggestion = self.getCache('suggestion_cached')
        if cached_suggestion:
            suggestions = cached_suggestion
        else:

            if not movies or len(movies) == 0:
                db = get_session()
                active_movies = db.query(Media) \
                    .options(joinedload_all('library')) \
                    .filter(or_(*[Media.status.has(identifier = s) for s in ['active', 'done']])).all()
                movies = [x.library.identifier for x in active_movies]

            if not ignored or len(ignored) == 0:
                ignored = splitString(Env.prop('suggest_ignore', default = ''))
            if not seen or len(seen) == 0:
                movies.extend(splitString(Env.prop('suggest_seen', default = '')))

            suggestions = fireEvent('movie.suggest', movies = movies, ignore = ignored, single = True)
            self.setCache('suggestion_cached', suggestions, timeout = 6048000)  # Cache for 10 weeks

        return {
            'success': True,
            'count': len(suggestions),
            'suggestions': suggestions[:int(limit)]
        }

    def ignoreView(self, imdb = None, limit = 6, remove_only = False, mark_seen = False, **kwargs):

        ignored = splitString(Env.prop('suggest_ignore', default = ''))
        seen = splitString(Env.prop('suggest_seen', default = ''))

        new_suggestions = []
        if imdb:
            if mark_seen:
                seen.append(imdb)
                Env.prop('suggest_seen', ','.join(set(seen)))
            elif not remove_only:
                ignored.append(imdb)
                Env.prop('suggest_ignore', ','.join(set(ignored)))

            new_suggestions = self.updateSuggestionCache(ignore_imdb = imdb, limit = limit, ignored = ignored, seen = seen)

        return {
            'result': True,
            'ignore_count': len(ignored),
            'suggestions': new_suggestions[limit - 1:limit]
        }

    def updateSuggestionCache(self, ignore_imdb = None, limit = 6, ignored = None, seen = None):

        # Combine with previous suggestion_cache
        cached_suggestion = self.getCache('suggestion_cached') or []
        new_suggestions = []
        ignored = [] if not ignored else ignored
        seen = [] if not seen else seen

        if ignore_imdb:
            suggested_imdbs = []
            for cs in cached_suggestion:
                if cs.get('imdb') != ignore_imdb and cs.get('imdb') not in suggested_imdbs:
                    suggested_imdbs.append(cs.get('imdb'))
                    new_suggestions.append(cs)

        # Get new results and add them
        if len(new_suggestions) - 1 < limit:

            active_status, done_status = fireEvent('status.get', ['active', 'done'], single = True)

            db = get_session()
            active_movies = db.query(Media) \
                .join(Library) \
                .with_entities(Library.identifier) \
                .filter(Media.status_id.in_([active_status.get('id'), done_status.get('id')])).all()
            movies = [x[0] for x in active_movies]
            movies.extend(seen)

            ignored.extend([x.get('imdb') for x in cached_suggestion])
            suggestions = fireEvent('movie.suggest', movies = movies, ignore = removeDuplicate(ignored), single = True)

            if suggestions:
                new_suggestions.extend(suggestions)

        self.setCache('suggestion_cached', new_suggestions, timeout = 3024000)

        return new_suggestions
