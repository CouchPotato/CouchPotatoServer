from couchpotato.api import addApiView
from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.logger import CPLog
from couchpotato.core.plugins.base import Plugin
from couchpotato.environment import Env

log = CPLog(__name__)

autoload = 'Automation'


class Automation(Plugin):

    def __init__(self):

        addEvent('app.load', self.setCrons)

        if not Env.get('dev'):
            addEvent('app.load', self.addMovies)

        addApiView('automation.add_movies', self.addMoviesFromApi, docs = {
            'desc': 'Manually trigger the automation scan. Hangs until scan is complete. Useful for webhooks.',
            'return': {'type': 'object: {"success": true}'},
        })
        addEvent('setting.save.automation.hour.after', self.setCrons)

    def setCrons(self):
        fireEvent('schedule.interval', 'automation.add_movies', self.addMovies, hours = self.conf('hour', default = 12))

    def addMoviesFromApi(self, **kwargs):
        self.addMovies()
        return {
            'success': True
        }

    def addMovies(self):

        movies = fireEvent('automation.get_movies', merge = True)
        movie_ids = []

        for imdb_id in movies:

            if self.shuttingDown():
                break

            prop_name = 'automation.added.%s' % imdb_id
            added = Env.prop(prop_name, default = False)
            if not added:
                added_movie = fireEvent('movie.add', params = {'identifier': imdb_id}, force_readd = False, search_after = False, update_after = True, single = True)
                if added_movie:
                    movie_ids.append(added_movie['_id'])
                Env.prop(prop_name, True)

        for movie_id in movie_ids:

            if self.shuttingDown():
                break

            movie_dict = fireEvent('media.get', movie_id, single = True)
            if movie_dict:
                fireEvent('movie.searcher.single', movie_dict)

        return True


config = [{
    'name': 'automation',
    'order': 101,
    'groups': [
        {
            'tab': 'automation',
            'name': 'automation',
            'label': 'Minimal movie requirements',
            'options': [
                {
                    'name': 'year',
                    'default': 2011,
                    'type': 'int',
                },
                {
                    'name': 'votes',
                    'default': 1000,
                    'type': 'int',
                },
                {
                    'name': 'rating',
                    'default': 7.0,
                    'type': 'float',
                },
                {
                    'name': 'hour',
                    'advanced': True,
                    'default': 12,
                    'label': 'Check every',
                    'type': 'int',
                    'unit': 'hours',
                    'description': 'hours',
                },
                {
                    'name': 'required_genres',
                    'label': 'Required Genres',
                    'default': '',
                    'placeholder': 'Example: Action, Crime & Drama',
                    'description': ('Ignore movies that don\'t contain at least one set of genres.', 'Sets are separated by "," and each word within a set must be separated with "&"')
                },
                {
                    'name': 'ignored_genres',
                    'label': 'Ignored Genres',
                    'default': '',
                    'placeholder': 'Example: Horror, Comedy & Drama & Romance',
                    'description': 'Ignore movies that contain at least one set of genres. Sets work the same as above.'
                },
            ],
        },
    ],
}]
