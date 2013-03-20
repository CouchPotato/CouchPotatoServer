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
import urllib

class NZBIndex(NZBDownloader):
    
    def __init__(self):
        super(NZBIndex, self).__init__()
        self.agreed = False

    def agree(self):
        self.opener.open("http://www.nzbindex.nl/agree/", urllib.urlencode( {'agree' : 'I agree' } ) )
        self.agreed = True

    def search(self, filename, minSize, newsgroup=None):
        
        if not self.agreed:
            self.agree()

        suffixURL = urllib.urlencode({'hidespam' : 1, 'more' : 0, 'max': '25', 'minsize' : minSize, 'q' : filename})
        refererURL = "http://www.nzbindex.nl/search/?" + suffixURL

        nzbIndexSoup = BeautifulSoup( self.open(refererURL) )
        
        results = nzbIndexSoup.findAll("tr", {"class" : "odd"}) + nzbIndexSoup.findAll("tr", {"class" : "even"})
                             
        for tr in results:
            nzblink = tr.find("a", text="Download")
            
            return NZBGetURLSearchResult(self, nzblink.get("href"), None, refererURL)
