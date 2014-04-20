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
        'search': 'https://www.nzbindex.nl/rss/?%s',
    }

    http_time_between_calls = 1 # Seconds
    
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
