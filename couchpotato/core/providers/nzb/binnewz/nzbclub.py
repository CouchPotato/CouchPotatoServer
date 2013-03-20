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

import urllib
import re
from bs4 import BeautifulSoup
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBGetURLSearchResult
import time

def isResultRow(tag):
    if tag and tag.has_key('class'):
        rowClass = tag['class']
        return rowClass[0] == 'rgRow' or rowClass[0] == 'rgAltRow'
    return False

def isInfoLabelSpan(tag):
    if tag and tag.has_key('id'):
        tagId = tag['id']
        return tagId.endswith("_InfoLabel")
    return False

class NZBClub(NZBDownloader):
    
    def __init__(self):
        NZBDownloader.__init__(self)

    def search(self, filename, minSize, newsgroup=None):

        if newsgroup:
            nzbClubURLs = [ urllib.urlencode({'q' : '"' + filename + '"', 'qg' : newsgroup }), urllib.urlencode({'q' : filename, 'qg' : newsgroup}) ]
        else:
            nzbClubURLs = [ urllib.urlencode({'q' : '"' + filename + '"'}), urllib.urlencode({'q' : filename}) ]
        
        for suffixURL in nzbClubURLs:

            nzbClubURL = "http://www.nzbclub.com/search.aspx?" + suffixURL
            
            nzbClubSoup = BeautifulSoup( self.open(nzbClubURL).read().decode('utf-8','ignore'))
            
            if nzbClubSoup:
                sizeInMegs = None
                for row in nzbClubSoup.findAll(isResultRow):
                    sizeSpan = row.find(isInfoLabelSpan)
                    sizeMatch = re.search("\[\s+([0-9]+\.[0-9]+)\s+(.)B ]", sizeSpan.text)
                    if not sizeMatch:
                        continue

                    sizeCount = float(sizeMatch.group(1))
                    sizeUnit = sizeMatch.group(2)
                    
                    if sizeUnit == 'K':
                        sizeInMegs = sizeCount / 1024
                    elif sizeUnit == 'G':
                        sizeInMegs = sizeCount * 1024
                    else:
                        sizeInMegs = sizeCount
                        
                    if minSize and sizeInMegs < minSize:
                        # ignoring result : too small
                        continue

                    downloadNZBImg = row.find("img", alt="Get NZB")
                    if downloadNZBImg:
                        downloadNZBLink = downloadNZBImg.parent
                        return NZBGetURLSearchResult( self, "http://www.nzbclub.com" + downloadNZBLink["href"], sizeInMegs, nzbClubURL)