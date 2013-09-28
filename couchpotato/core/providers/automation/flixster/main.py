from couchpotato.core.helpers.variable import tryInt, splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import json

log = CPLog(__name__)


class Flixster(Automation):

    url = 'http://www.flixster.com/api/users/%s/movies/ratings?scoreTypes=wts'

    interval = 60

    def getIMDBids(self):

        ids = splitString(self.conf('automation_ids'))

        if len(ids) == 0:
            return []

        movies = []

        for movie in self.getWatchlist():
            imdb_id = self.search(movie.get('title'), movie.get('year'), imdb_only = True)
            movies.append(imdb_id)

        return movies

    def getWatchlist(self):

        enablers = [tryInt(x) for x in splitString(self.conf('automation_ids_use'))]
        ids = splitString(self.conf('automation_ids'))

        index = -1
        movies = []
        for user_id in ids:

            index += 1
            if not enablers[index]:
                continue

            data = json.loads(self.getHTMLData(self.url % user_id))

            for movie in data:
                movies.append({'title': movie['movie']['title'], 'year': movie['movie']['year'] })

        return movies
