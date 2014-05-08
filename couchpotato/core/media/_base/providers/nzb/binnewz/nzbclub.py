from bs4 import BeautifulSoup
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBGetURLSearchResult
from couchpotato.core.helpers.encoding import toUnicode,tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.media._base.providers.nzb.base import NZBProvider
from dateutil.parser import parse
import time
log = CPLog(__name__)
class NZBClub(NZBDownloader, NZBProvider, RSS):
    
    urls = {
        'search': 'http://www.nzbclub.com/nzbfeeds.aspx?%s',
    }

    http_time_between_calls = 4 #seconds

    def search(self, filename, minSize, newsgroup=None):

        q = filename

        params = tryUrlencode({
            'q': q,
            'qq': newsgroup,
            'ig': 1,
            'rpp': 200,
            'st': 5,
            'sp': 1,
            'ns': 1,
        })
        
        nzbs = self.getRSSData(self.urls['search'] % params)

        for nzb in nzbs:

            nzbclub_id = tryInt(self.getTextElement(nzb, "link").split('/nzb_view/')[1].split('/')[0])
            enclosure = self.getElement(nzb, "enclosure").attrib
            size = enclosure['length']
            date = self.getTextElement(nzb, "pubDate")

            def extra_check(item):
                full_description = self.getCache('nzbclub.%s' % nzbclub_id, item['detail_url'], cache_timeout = 25920000)

                for ignored in ['ARCHIVE inside ARCHIVE', 'Incomplete', 'repair impossible']:
                    if ignored in full_description:
                        log.info('Wrong: Seems to be passworded or corrupted files: %s', item['name'])
                #        return False

                #return True
            nzbid = nzbclub_id
                #'name': toUnicode(self.getTextElement(nzb, "title")),
            age = self.calculateAge(int(time.mktime(parse(date).timetuple())))
            sizeInMegs = (tryInt(size)/1024/1024)
            downloadUrl = enclosure['url'].replace(' ', '_')
            nzbClubURL = self.getTextElement(nzb, "link")
                #'get_more_info': self.getMoreInfo,
                #'extra_check': extra_check

                   
            return NZBGetURLSearchResult( self, downloadUrl, sizeInMegs, nzbClubURL, age, nzbid)
            
                