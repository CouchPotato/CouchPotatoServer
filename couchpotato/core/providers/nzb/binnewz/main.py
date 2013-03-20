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

from binsearch import BinSearch
from nzbclub import NZBClub
from nzbindex import NZBIndex

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.nzb.base import NZBProvider

log = CPLog(__name__)
import re
import urllib
import urllib2

class BinNewzProvider(NZBProvider):
    
    urls = {
        'download': 'http://www.binnews.in/',
        'detail': 'http://www.binnews.in/',
        'search': 'http://www.binnews.in/',
    }

    http_time_between_calls = 4 # Seconds
    cat_backup_id = None
    
    def _search(self, movie, quality, results):
        nzbDownloaders = [ NZBIndex(), NZBClub(), BinSearch() ]
        TitleStringReal = getTitle(movie['library']).encode("utf-8")
        moviequality = simplifyString(quality['identifier'])
        if moviequality in ("720p","1080p","bd50"):
            cat='39'
            minSize = 2000
        elif moviequality in ("dvdr"):
            cat='23'
            minSize = 3000
        else:
            cat='6'
            minSize = 500      
       
        data = urllib.urlencode({'b_submit': 'BinnewZ', 'cats[]' : cat, 'edSearchAll' : TitleStringReal, 'sections[]': ''})
        
        try:
            soup = BeautifulSoup( urllib2.urlopen("http://www.binnews.in/_bin/search2.php", data) )
        except Exception, e:
            log.error(u"Error trying to load BinNewz response: "+e)
            return []
        
        #results = []

        tables = soup.findAll("table", id="tabliste")
        for table in tables:

            rows = table.findAll("tr")
            for row in rows:
                
                cells = row.select("> td")
                if (len(cells) < 11):
                    continue

                name = cells[2].text.strip()
                language = cells[3].find("img").get("src")

                if not "_fr" in language:
                    continue
                                                
  
                # blacklist_groups = [ "alt.binaries.multimedia" ]
                blacklist_groups = []                
                
                newgroupLink = cells[4].find("a")
                newsgroup = None
                if newgroupLink.contents:
                    newsgroup = newgroupLink.contents[0]
                    if newsgroup == "abmulti":
                        newsgroup = "alt.binaries.multimedia"
                    elif newsgroup == "abtvseries":
                        newsgroup = "alt.binaries.tvseries"
                    elif newsgroup == "abtv":
                        newsgroup = "alt.binaries.tv"
                    elif newsgroup == "a.b.teevee":
                        newsgroup = "alt.binaries.teevee"
                    elif newsgroup == "abstvdivxf":
                        newsgroup = "alt.binaries.series.tv.divx.french"
                    elif newsgroup == "abhdtvx264fr":
                        newsgroup = "alt.binaries.hdtv.x264.french"
                    elif newsgroup == "abmom":
                        newsgroup = "alt.binaries.mom"  
                    elif newsgroup == "abhdtv":
                        newsgroup = "alt.binaries.hdtv"
                    elif newsgroup == "abboneless":
                        newsgroup = "alt.binaries.boneless"
                    elif newsgroup == "abhdtvf":
                        newsgroup = "alt.binaries.hdtv.french"
                    elif newsgroup == "abhdtvx264":
                        newsgroup = "alt.binaries.hdtv.x264"
                    elif newsgroup == "absuperman":
                        newsgroup = "alt.binaries.superman"
                    elif newsgroup == "abechangeweb":
                        newsgroup = "alt.binaries.echange-web"
                    elif newsgroup == "abmdfvost":
                        newsgroup = "alt.binaries.movies.divx.french.vost"
                    elif newsgroup == "abdvdr":
                        newsgroup = "alt.binaries.dvdr"
                    elif newsgroup == "abmzeromov":
                        newsgroup = "alt.binaries.movies.zeromovies"
                    elif newsgroup == "abcfaf":
                        newsgroup = "alt.binaries.cartoons.french.animes-fansub"
                    elif newsgroup == "abcfrench":
                        newsgroup = "alt.binaries.cartoons.french"
                    elif newsgroup == "abgougouland":
                        newsgroup = "alt.binaries.gougouland"
                    elif newsgroup == "abroger":
                        newsgroup = "alt.binaries.roger"
                    elif newsgroup == "abtatu":
                        newsgroup = "alt.binaries.tatu"
                    elif newsgroup =="abstvf":
                        newsgroup = "alt.binaries.series.tv.french"
                    elif newsgroup =="abmdfreposts":
                        newsgroup="alt.binaries.movies.divx.french.reposts"
                    elif newsgroup =="abmdf":
                        newsgroup="alt.binaries.movies.french"
                    else:
                        log.error(u"Unknown binnewz newsgroup: " + newsgroup)
                        continue
                    
                    if newsgroup in blacklist_groups:
                        log.error(u"Ignoring result, newsgroup is blacklisted: " + newsgroup)
                        continue
   
                filename =  cells[5].contents[0]
    
                m =  re.search("^(.+)\s+{(.*)}$", name)
                qualityStr = ""
                if m:
                    name = m.group(1)
                    qualityStr = m.group(2)
    
                m =  re.search("^(.+)\s+\[(.*)\]$", name)
                source = None
                if m:
                    name = m.group(1)
                    source = m.group(2)

                m =  re.search("(.+)\(([0-9]{4})\)", name)
                year = ""
                if m:
                    name = m.group(1)
                    year = m.group(2)
    
                m =  re.search("(.+)\((\d{2}/\d{2}/\d{4})\)", name)
                dateStr = ""
                if m:
                    name = m.group(1)
                    dateStr = m.group(2)
    
                m =  re.search("(.+)\s+S(\d{2})\s+E(\d{2})(.*)", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)
    
                m =  re.search("(.+)\s+S(\d{2})\s+Ep(\d{2})(.*)", name)
                if m:
                    name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)
                    
                        
                filenameLower = filename.lower()
                                                
                searchItems = []
                
                if len(searchItems) == 0 and qualityStr == moviequality :
                    searchItems.append( filename )
                id=10000
                for searchItem in searchItems:
                    for downloader in nzbDownloaders:
                        log.info2("Searching for download : " + name + ", search string = "+ searchItem + " on " + downloader.__class__.__name__)
                        try:
                            binsearch_result =  downloader.search(searchItem, minSize, newsgroup )
                            if binsearch_result:
                                new={}
                                binsearch_result.title = name
                                binsearch_result.quality = quality
                                def extra_check(item):
                                    return True
                                new['id'] = id
                                new['name'] = searchItem + ' french ' + qualityStr +' '+ name +' ' + downloader.__class__.__name__ 
                                new['url'] = binsearch_result.nzburl
                                new['detail_url'] = binsearch_result.refererURL
                                new['size'] = binsearch_result.sizeInMegs
                                new['age'] = 10
                                new['extra_check'] = extra_check
    
                                results.append(new)
                                
                                id=id+1
                                log.info2("Found : " + searchItem + " on " + downloader.__class__.__name__)
                                break
                        except Exception, e:
                            log.error("Searching from " + downloader.__class__.__name__ + " failed : " + str(e))
    def download(self, url = '', nzb_id = ''):

        params = {'action': 'nzb'}
        params[nzb_id] = 'on'

        try:
            return self.urlopen(url, params = params, show_error = False)
        except:
            log.error('Failed getting nzb from %s: %s', (self.getName()))

        return 'try_next'