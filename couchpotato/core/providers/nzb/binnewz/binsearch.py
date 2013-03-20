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
from bs4 import BeautifulSoup
import re
from nzbdownloader import NZBDownloader
from nzbdownloader import NZBPostURLSearchResult

class BinSearch(NZBDownloader):
    
    def search(self, filename, minSize, newsgroup=None):

        if newsgroup != None:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'adv_g' : newsgroup, 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'adv_g' : newsgroup, 'q' : filename})]
        else:
            binSearchURLs = [  urllib.urlencode({'server' : 1, 'max': '250', 'q' : filename}), urllib.urlencode({'server' : 2, 'max': '250', 'q' : filename})]

        for suffixURL in binSearchURLs:
            binSearchURL = "http://binsearch.info/?adv_age=&" + suffixURL
                    
            binSearchSoup = BeautifulSoup( self.open(binSearchURL) )

            foundName = None
            sizeInMegs = None
            for elem in binSearchSoup.findAll(lambda tag: tag.name=='tr' and tag.get('bgcolor') == '#FFFFFF' and 'size:' in tag.text):
                for checkbox in elem.findAll(lambda tag: tag.name=='input' and tag.get('type') == 'checkbox'):
                    sizeStr = re.search("size:\s+([^B]*)B", elem.text).group(1).strip()
                    
                    if "G" in sizeStr:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) ) * 1024
                    elif "K" in sizeStr:
                        sizeInMegs = 0
                    else:
                        sizeInMegs = float( re.search("([0-9\\.]+)", sizeStr).group(1) )
                    
                    if sizeInMegs > minSize:
                        foundName = checkbox.get('name')
                        break
                
            if foundName:
                postData = urllib.urlencode({foundName: 'on', 'action': 'nzb'})
                nzbURL = "http://binsearch.info/fcgi/nzb.fcgi?adv_age=&" + suffixURL
                return NZBPostURLSearchResult( self, nzbURL, postData, sizeInMegs, binSearchURL )
                    