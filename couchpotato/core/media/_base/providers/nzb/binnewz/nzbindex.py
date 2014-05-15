from bs4 import BeautifulSoup
from nzbdownloader import NZBDownloader, NZBGetURLSearchResult
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from couchpotato.environment import Env
from dateutil.parser import parse
import urllib
import time
log = CPLog(__name__)

class NZBIndex(NZBDownloader,NZBProvider, RSS):
    
    urls = {
        'download': 'https://www.nzbindex.nl/download/',
        'search': 'http://www.nzbindex.com/rss/?%s',
    }

    http_time_between_calls = 5 # Seconds
    
    def search(self, filename, minSize, newsgroup=None):
        
        q = filename
        arguments = tryUrlencode({
            'q': q,
            'age': Env.setting('retention', 'nzb'),
            'sort': 'agedesc',
            'minsize': minSize,
            'rating': 1,
            'max': 250,
            'more': 1,
            'complete': 1,
        })
        nzbs = self.getRSSData(self.urls['search'] % arguments)
        nzbid = None
        for nzb in nzbs:

            enclosure = self.getElement(nzb, 'enclosure').attrib
            nzbindex_id = int(self.getTextElement(nzb, "link").split('/')[4])

        
            nzbid = nzbindex_id 
            age = self.calculateAge(int(time.mktime(parse(self.getTextElement(nzb, "pubDate")).timetuple())))
            sizeInMegs = tryInt(enclosure['length']) / 1024 / 1024
            downloadUrl = enclosure['url']
            detailURL = enclosure['url'].replace('/download/', '/release/')
            
        if nzbid:
            return NZBGetURLSearchResult(self, downloadUrl, sizeInMegs, detailURL, age, nzbid)
