import base64
import time
import json

from couchpotato.core.event import addEvent, fireEvent
from couchpotato.core.helpers.encoding import tryUrlencode, ss
from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.base import MovieProvider
from couchpotato.environment import Env


log = CPLog(__name__)

autoload = 'CouchPotatoApi'


class CouchPotatoApi(MovieProvider):

    urls = {
        'validate': 'https://api.couchpota.to/validate/%s/',
        'search': 'https://api.couchpota.to/search/%s/',
        'info': 'https://api.couchpota.to/info/%s/',
        'is_movie': 'https://api.couchpota.to/ismovie/%s/',
        'eta': 'https://api.couchpota.to/eta/%s/',
        'suggest': 'https://api.couchpota.to/suggest/',
        'updater': 'https://api.couchpota.to/updater/?%s',
        'messages': 'https://api.couchpota.to/messages/?%s',
    }
    http_time_between_calls = 0
    api_version = 1

    def __init__(self):
        addEvent('movie.info', self.getInfo, priority = 2)
        addEvent('movie.info.release_date', self.getReleaseDate)

        addEvent('info.search', self.search, priority = 1)
        addEvent('movie.search', self.search, priority = 1)

        addEvent('movie.suggest', self.getSuggestions)
        addEvent('movie.is_movie', self.isMovie)

        addEvent('release.validate', self.validate)

        addEvent('cp.api_call', self.call)

        addEvent('cp.source_url', self.getSourceUrl)
        addEvent('cp.messages', self.getMessages)

    def call(self, url, **kwargs):
        return self.getJsonData(url, headers = self.getRequestHeaders(), **kwargs)

    def getMessages(self, last_check = 0):

        data = self.getJsonData(self.urls['messages'] % tryUrlencode({
            'last_check': last_check,
        }), headers = self.getRequestHeaders(), cache_timeout = 10)

        return data

    def getSourceUrl(self, repo = None, repo_name = None, branch = None):
        return self.getJsonData(self.urls['updater'] % tryUrlencode({
            'repo': repo,
            'name': repo_name,
            'branch': branch,
        }), headers = self.getRequestHeaders())

    def search(self, q, limit = 5):
        return self.getJsonData(self.urls['search'] % tryUrlencode(q) + ('?limit=%s' % limit), headers = self.getRequestHeaders())

    def validate(self, name = None):

        if not name:
            return

        name_enc = base64.b64encode(ss(name))
        return self.getJsonData(self.urls['validate'] % name_enc, headers = self.getRequestHeaders())

    def isMovie(self, identifier = None, adding = False, **kwargs):

        if not identifier:
            return

        url = self.urls['is_movie'] % identifier
        url += '' if adding else '?ignore=1'

        data = self.getJsonData(url, headers = self.getRequestHeaders())
        if data:
            return data.get('is_movie', True)

        return True

    def getInfo(self, identifier = None, adding = False, **kwargs):

        if not identifier:
            return

        url = self.urls['info'] % identifier
        url += '' if adding else '?ignore=1'

        result = self.getJsonData(url, headers = self.getRequestHeaders())
        if result:
            return dict((k, v) for k, v in result.items() if v)

        return {}

    def getReleaseDate(self, identifier = None):
        if identifier is None: return {}

        dates = self.getJsonData(self.urls['eta'] % identifier, headers = self.getRequestHeaders())

        #This grabs release date info from omdbapi/rottentomatoes
        temp2 = self.getJsonData("http://www.omdbapi.com/?i=%s&tomatoes=true&plot=short&r=json" % identifier)
        #log.debug(temp2)
        ddate=0 #throw away what couchpotatoai is returning since it is garbage at this time
        tdate=0
        dvd_date= temp2['DVD']
        theater_date=temp2['Released']
        if theater_date != 'N/A':
            p='%d %b %Y'
            tdate=int(time.mktime(time.strptime(theater_date,p)))

        if dvd_date != 'N/A':
            p='%d %b %Y'
            ddate=int(time.mktime(time.strptime(dvd_date,p)))
           
        if (ddate !=0):    
            if ddate < tdate:
                ddate = 0 #if the dvd release date occurs before the theater release date, assume the data is wrong
                tdate = 0
        dates['dvd']=ddate    
        dates['theater']=tdate
        """
        #This grabs release date info for US from themoviedb - one must replace xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx with their themoviedb api key
        #note - if more than one release date of a particular type is found, the last one found will be used
        #im just throwing this code in here because obviously the couchpotato api method of grabbing release date info and eta's is broken
        #or not working
        #perhaps the fix shouldnt be done right here; however, I am just checking this code in because perhaps someone who knows
        #how couchpotato works better can use this code in a more appropriate way to make couchpotato eta more robust.
        #temp = self.getJsonData("https://api.themoviedb.org/3/movie/%s/release_dates?api_key=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" % identifier)
        results = temp['results']
        theater_rel=''
        dvd_rel=''
        p='%Y-%m-%d'
        for result in results:
            country = result['iso_3166_1']
            if country == 'US':
                rds = result['release_dates']
                for rd in rds:
                    rd_type=rd['type']
                    if rd_type ==2 or rd_type==3:   #is theatrical release date
                       theater_rel = rd['release_date']
                    elif rd_type == 4 or rd_type == 5:   #is digital or dvd release date
                       dvd_rel = rd['release_date']
        if theater_rel != '':
            tdate=int(time.mktime(time.strptime(theater_rel[:10],p)))
        	 
        if dvd_rel !='':
            ddate=int(time.mktime(time.strptime(dvd_rel[:10],p)))
        if tdate > ddate: #dont write the data unless its good and makes sense
            dates['theater']=tdate
            dates['dvd']=ddate	
        #"""


        log.debug('Found ETA for %s: %s', (identifier, dates))
        return dates

    def getSuggestions(self, movies = None, ignore = None):
        if not ignore: ignore = []
        if not movies: movies = []

        suggestions = self.getJsonData(self.urls['suggest'], data = {
            'movies': ','.join(movies),
            'ignore': ','.join(ignore),
        }, headers = self.getRequestHeaders())
        log.info('Found suggestions for %s movies, %s ignored', (len(movies), len(ignore)))

        return suggestions

    def getRequestHeaders(self):
        return {
            'X-CP-Version': fireEvent('app.version', single = True),
            'X-CP-API': self.api_version,
            'X-CP-Time': time.time(),
            'X-CP-Identifier': '+%s' % Env.setting('api_key', 'core')[:10],  # Use first 10 as identifier, so we don't need to use IP address in api stats
        }
