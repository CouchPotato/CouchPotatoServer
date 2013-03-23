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

import urllib2
from StringIO import StringIO
import gzip
import cookielib
import time

class NZBDownloader(object):

    def __init__( self ):
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))        
        self.lastRequestTime = None
        
    def waitBeforeNextRequest(self):
        if self.lastRequestTime and self.lastRequestTime > ( time.mktime(time.localtime()) - 10):
            time.sleep( 10 )
        self.lastRequestTime = time.gmtime()
        
    def open(self, request):
        self.waitBeforeNextRequest()
        return self.opener.open(request)
        
class NZBSearchResult(object):
    
    def __init__(self, downloader, sizeInMegs, refererURL, age, nzbid):
        self.downloader = downloader
        self.refererURL = refererURL
        self.sizeInMegs = sizeInMegs
        self.age = age
        self.nzbid = nzbid
    def readRequest(self, request):
        request.add_header('Accept-encoding', 'gzip')
        request.add_header('Referer', self.refererURL)
        request.add_header('Accept-Encoding', 'gzip')
        request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.57 Safari/537.17')

        response = self.downloader.open(request)
        if response.info().get('Content-Encoding') == 'gzip':
            buf = StringIO( response.read())
            f = gzip.GzipFile(fileobj=buf)
            return f.read()
        else:
            return response.read()      
        
    def getNZB(self):
        pass          
        
class NZBGetURLSearchResult( NZBSearchResult ):

    def __init__(self, downloader, nzburl, sizeInMegs, refererURL, age, nzbid):
        NZBSearchResult.__init__(self, downloader, sizeInMegs, refererURL, age, nzbid)
        self.nzburl = nzburl
        
    def getNZB(self):
        request = urllib2.Request( self.nzburl )
        self.nzbdata = NZBSearchResult.readRequest( self, request )
        return self.nzbdata

class NZBPostURLSearchResult( NZBSearchResult ):

    def __init__(self, downloader, nzburl, postData, sizeInMegs, refererURL, age, nzbid):
        NZBSearchResult.__init__(self, downloader, sizeInMegs, refererURL, age, nzbid)
        self.nzburl = nzburl
        self.postData = postData
        
    def getNZB(self):
        request = urllib2.Request( self.nzburl, self.postData )
        self.nzbdata = NZBSearchResult.readRequest( self, request )
        return self.nzbdata

class NZBDataSearchResult( NZBSearchResult ):

    def __init__(self, nzbdata, sizeInMegs, refererURL, age, nzbid):
        NZBSearchResult.__init__(self, None, refererURL, age, nzbid)
        self.nzbdata = nzbdata

    def getNZB(self):
        return self.nzbdata
        