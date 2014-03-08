# Author: Guillaume Serre <guillaume.serre@gmail.com>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.

from bs4 import BeautifulSoup
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBGetURLSearchResult
from couchpotato.core.helpers.encoding import toUnicode,tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.rss import RSS
from couchpotato.core.providers.nzb.base import NZBProvider
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
            
                