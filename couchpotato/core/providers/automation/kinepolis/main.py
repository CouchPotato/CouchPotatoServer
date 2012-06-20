from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, getImdb, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
from couchpotato.environment import Env
from dateutil.parser import parse
from urllib import quote_plus
import time
import traceback
import xml.etree.ElementTree as XMLTree
import datetime
import json

log = CPLog(__name__)


class Kinepolis(Automation, RSS):

    interval = 1800
    rss_url = 'http://kinepolis.be/nl/top10-box-office/feed'

    def getIMDBids(self):
        
        if self.isDisabled():
            return
        
        movies = []
        RSSMovie = {'name': 'placeholder', 'year' : 'placeholder'}

	cache_key = 'kinepolis.%s' % md5(self.rss_url)
	rss_data = self.getCache(cache_key, self.rss_url)
	data = XMLTree.fromstring(rss_data)

	if data:
	    rss_movies = self.getElements(data, 'channel/item')
	    
	    for movie in rss_movies:
                RSSMovie['name'] = self.getTextElement(movie, "title")
                currentYear = datetime.datetime.now().strftime("%Y")
                RSSMovie['year'] = currentYear

                log.info('Release found: %s.' % RSSMovie)
		imdbId = self.getIMDBFromTitle(RSSMovie['name'])
                movies.append(imdbId)

        return movies

    def getIMDBFromTitle(self,title):
        api_url = self.createApiUrl()
        search_url = api_url + '/movie.search/?q=' + quote_plus(title)
        data = self.urlopen(search_url)
        jsondata = json.loads(data)
        return jsondata['movies'][0]['imdb']

    def createBaseUrl(self):
        host = Env.setting('host')
        if host == '0.0.0.0':
            host = 'localhost'
        port = Env.setting('port')

        return '%s:%d%s' % (cleanHost(host).rstrip('/'), int(port), '/' + Env.setting('url_base').lstrip('/') if Env.setting('url_base') else '')

    def createApiUrl(self):
        return '%s/api/%s' % (self.createBaseUrl(), Env.setting('api_key'))



