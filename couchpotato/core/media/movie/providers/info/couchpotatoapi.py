import base64
import time
import json
import requests

from datetime import date
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
        title = temp2['Title']
        year = int(temp2['Year'])

        #log.debug(title)
        ddate=0 #throw away what couchpotatoai is returning since it is garbage at this time
        tdate=0
        dvd_date= temp2['DVD']
        theater_date=temp2['Released']
        if theater_date != 'N/A' and year >1972:
            p='%d %b %Y'
            tdate=int(time.mktime(time.strptime(theater_date,p)))

        if dvd_date != 'N/A' and year >1972:
            p='%d %b %Y'
            ddate=int(time.mktime(time.strptime(dvd_date,p)))
           
        if (ddate !=0):    
            if ddate < tdate:
                ddate = 0 #if the dvd release date occurs before the theater release date, assume the data is wrong
                tdate = 0
        dates['dvd']=ddate    
        dates['theater']=tdate
        dates['netflix']=0

        #specify netflix region by its country code
        countryCode='us' #United States #this would be the default
        countryCode='ca'  #Canada #this should be read in from config file but hardcoding for now
        #other countries are supported by allflicks.net, so other country codes could be added
        #but the session heads must be adjusted accordingly or proper JSON wont be returned
        #firefox extension tamper is useful for determining country code/appropriate headers for a country
        now_year = date.today().year

        url = 'https://www.allflicks.net/wp-content/themes/responsive/processing/processing_%s.php?draw=9&columns[0][data]=box_art&columns[0][name]=&columns[0][searchable]=true&columns[0][orderable]=false&columns[0][search][value]=&columns[0][search][regex]=false&columns[1][data]=title&columns[1][name]=&columns[1][searchable]=true&columns[1][orderable]=true&columns[1][search][value]=&columns[1][search][regex]=false&columns[2][data]=year&columns[2][name]=&columns[2][searchable]=true&columns[2][orderable]=true&columns[2][search][value]=&columns[2][search][regex]=false&columns[3][data]=genre&columns[3][name]=&columns[3][searchable]=true&columns[3][orderable]=true&columns[3][search][value]=&columns[3][search][regex]=false&columns[4][data]=rating&columns[4][name]=&columns[4][searchable]=true&columns[4][orderable]=true&columns[4][search][value]=&columns[4][search][regex]=false&columns[5][data]=available&columns[5][name]=&columns[5][searchable]=true&columns[5][orderable]=true&columns[5][search][value]=&columns[5][search][regex]=false&columns[6][data]=director&columns[6][name]=&columns[6][searchable]=true&columns[6][orderable]=true&columns[6][search][value]=&columns[6][search][regex]=false&columns[7][data]=cast&columns[7][name]=&columns[7][searchable]=true&columns[7][orderable]=true&columns[7][search][value]=&columns[7][search][regex]=false&order[0][column]=5&order[0][dir]=desc&start=%s&length=%s&search[value]=%s&search[regex]=false&movies=true&shows=false&documentaries=true&rating=netflix&min=1900&max=%s&_=1478945015662'
        log.debug('-------------->querying Allflicks for title: %s' %title)
        #Please note if allflicks has the name listd with the wrong name, 
        # or imdb has the movie with a different title. This check will fail and 
        # the movie will not be reported as being on netflix when in fact it is.
        length=100
        start=0

        #since netflix doesnt always have the same title as IMDB
        #we could potentially use a user-specified title when querying allFlicks
        #the option still needs to be implemented 
        titleForNetflix = title
        numFound = 1 #this just forces at least one execution of the following loop
        while start < numFound and not year > now_year:
            with requests.Session() as session:
                session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:49.0) Gecko/20100101 Firefox/49.0"}
                if countryCode=='ca':
                    session.get("http://www.allflicks.net/canada/")
                    response = session.get(url % (countryCode,str(start),str(length),titleForNetflix,str(now_year)),headers={"Accept" : "application.json, text/javascript, */*; q=0.01",
                                                  "X-Requested-With": "XMLHttpRequest",
                                                  "Referer": "http://www.allflicks.net/canada/",
                                                  "Host": "www.allflicks.net"})
                else:
                    session.get("http://www.allflicks.net/") 
                    response = session.get(url % (countryCode,str(start),str(length),titleForNetflix,str(now_year)),headers={"Accept" : "application/json, text/javascript, */*; q=0.01", 
                                                 "X-Requested-With": "XMLHttpRequest", 
                                                 "Referer": "http://www.allflicks.net/", 
                                                 "Host": "www.allflicks.net"})
            
            j1= response.json()
            numFound = j1['recordsFiltered']
            if not numFound >0: break
            if start == 0: log.debug('----->Movie %s returned %s results from Allflicks' % (title,numFound))
            results = j1['data']
            for result in results:
                if result['title'].upper() == titleForNetflix.upper():   #this needs to be case insensitive
                    if int(result['year']) <= year+1 and int(result['year']) >= year-1:
                        log.debug('---> Movie %s (%s) matched with %s (%s)from Allflicks' % (title,str(year),result['title'], result['year']))
                        p='%d %b %Y'
                        ndate=int(time.mktime(time.strptime(result['available'],p)))
                        dates['netflix']=ndate
            start=start+length
        
        """
        #This grabs release date info for US from themoviedb - one must replace xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx with their themoviedb api key
        #note - if more than one release date of a particular type is found, the last one found will be used
        #im just throwing this code in here because obviously the couchpotato api method of grabbing release date info and eta's is broken
        #or not working
        #perhaps the fix shouldnt be done right here; however, I am just checking this code in because perhaps someone who knows
        #how couchpotato works better can use this code in a more appropriate way to make couchpotato eta more robust.
        #"""
        apiKey='' #apiKey should be '' or 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        if (dates['dvd'] or dates['theater']):
            log.debug('Found ETA using OMDBAPI for %s: %s', (identifier, dates))
            return dates
        if (apiKey == ''): 
            log.debug('Wanted to check ETA for %s on THEMOVIEDB but no apiKey specified' % identifier)
            return dates
        temp = self.getJsonData("https://api.themoviedb.org/3/movie/%s/release_dates?api_key=%s" % (identifier,apiKey))
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
        if theater_rel != '' and year > 1972:
            tdate=int(time.mktime(time.strptime(theater_rel[:10],p)))
        	 
        if dvd_rel !='' and year > 1972:
            ddate=int(time.mktime(time.strptime(dvd_rel[:10],p)))

        if (ddate !=0):    
            if ddate < tdate:
                ddate = 0 #if the dvd release date occurs before the theater release date, assume the data is wrong
                tdate = 0
        dates['dvd']=ddate    
        dates['theater']=tdate


        if (dates['theater'] or dates['dvd']):
            log.debug('Found ETA using THEMOVIEDB for %s: %s', (identifier, dates))
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
