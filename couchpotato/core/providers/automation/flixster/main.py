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
            
            # flixster returns the json with a couple anomalies that can break the json parsing
            # so we'll grab the data and "fix" it before trying to parse it
            json_string = self.getHTMLData(self.url % user_id)
            # first we have to strip extra newlines from the string
            json_string = json_string.strip()
            # then decode it using the given ISO-8859-1 encoding
            json_string = json_string.decode('iso-8859-1')
            # and re-encode it as utf-8
            json_string = json_string.encode('utf-8')
            # then we can pass it to the json parser
            data = json.loads(json_string)

            for movie in data:
                movies.append({'title': movie['movie']['title'], 'year': movie['movie']['year'] })

        return movies
