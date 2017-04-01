from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.variable import md5, getImdb, splitString, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.automation.base import Automation
import datetime
import xml.etree.ElementTree as XMLTree
from xml.etree.ElementTree import QName
import traceback

log = CPLog(__name__)


class ITunes(Automation, RSS):

    interval = 1800

    def getIMDBids(self):

        if self.isDisabled():
            return

        movies = []

        enablers = [tryInt(x) for x in splitString(self.conf('automation_urls_use'))]
        urls = splitString(self.conf('automation_urls'))

        namespace = 'http://www.w3.org/2005/Atom'
        namespaceIM = 'http://itunes.apple.com/rss'
        
        index = -1
        for url in urls:

            index += 1
            if not enablers[index]:
                continue

            try:
                cache_key = 'itunes.rss.%s' % md5(url)
                rss_data = self.getCache(cache_key, url)

                data = XMLTree.fromstring(rss_data)
                
                if data is not None:
                    entry_tag = str(QName(namespace, 'entry'))
                    rss_movies = self.getElements(data, entry_tag)
                    
                    for movie in rss_movies:
                        name_tag = str(QName(namespaceIM, 'name'))
                        name = self.getTextElement( movie, name_tag )
                        
                        releaseDate_tag = str(QName(namespaceIM, 'releaseDate')) 
                        releaseDateText = self.getTextElement(movie, releaseDate_tag)
                        year = datetime.datetime.strptime(releaseDateText, '%Y-%m-%dT00:00:00-07:00').strftime("%Y")
                        
                        imdb = self.search(name, year)
                        
                        if imdb and self.isMinimalMovie(imdb):
                            movies.append(imdb['imdb'])
            
            except:
                log.error('Failed loading iTunes rss feed: %s %s', (url, traceback.format_exc()))

        return movies
