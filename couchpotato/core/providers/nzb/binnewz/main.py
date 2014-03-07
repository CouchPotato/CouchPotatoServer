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
from couchpotato.core.helpers.variable import getTitle, splitString, tryInt
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.environment import Env
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers import namer_check
from couchpotato.core.providers.nzb.base import NZBProvider

log = CPLog(__name__)
import re
import urllib
import urllib2
import traceback
class BinNewz(NZBProvider):
    
    urls = {
        'download': 'http://www.binnews.in/',
        'detail': 'http://www.binnews.in/',
        'search': 'http://www.binnews.in/_bin/search2.php',
    }

    http_time_between_calls = 4 # Seconds
    cat_backup_id = None
    
    def _search(self, movie, quality, results):
        nzbDownloaders = [NZBClub(), BinSearch(), NZBIndex()]
        MovieTitles = movie['library']['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        movieyear = movie['library']['year']
        if moviequality in ("720p","1080p","bd50"):
            cat1='39'
            cat2='49'
            minSize = 2000
        elif moviequality in ("dvdr"):
            cat1='23'
            cat2='48'
            minSize = 3000
        else:
            cat1='6'
            cat2='27'
            minSize = 500
            
        for MovieTitle in MovieTitles:
            TitleStringReal = str(MovieTitle.encode("utf-8").replace('-',' '))
            data = 'chkInit=1&edTitre='+TitleStringReal+'&chkTitre=on&chkFichier=on&chkCat=on&cats%5B%5D='+cat1+'&cats%5B%5D='+cat2+'&edAge=&edYear='
            try:
                soup = BeautifulSoup( urllib2.urlopen(self.urls['search'], data) )
            except Exception, e:
                log.error(u"Error trying to load BinNewz response: "+e)
                return []
    
            tables = soup.findAll("table", id="tabliste")
            for table in tables:
    
                rows = table.findAll("tr")
                for row in rows:
                    
                    cells = row.select("> td")
                    if (len(cells) < 11):
                        continue
    
                    name = cells[2].text.strip()
                    testname=namer_check.correctName(name,movie)
                    if testname==0:
                        continue
                    language = cells[3].find("img").get("src")
    
                    if not "_fr" in language and not "_frq" in language:
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
                        elif newsgroup =="abhdtvfrepost":
                            newsgroup="alt.binaries.hdtv.french.repost"
                        elif newsgroup == "abmmkv":
                            newsgroup = "alt.binaries.movies.mkv"
                        elif newsgroup == "abf-tv":
                            newsgroup = "alt.binaries.french-tv"
                        elif newsgroup == "abmdfo":
                            newsgroup = "alt.binaries.movies.divx.french.old"
                        elif newsgroup == "abmf":
                            newsgroup = "alt.binaries.movies.french"
                        elif newsgroup == "ab.movies":
                            newsgroup = "alt.binaries.movies"
                        elif newsgroup == "a.b.french":
                            newsgroup = "alt.binaries.french"
                        elif newsgroup == "a.b.3d":
                            newsgroup = "alt.binaries.3d"
                        elif newsgroup == "ab.dvdrip":
                            newsgroup = "alt.binaries.dvdrip"
                        elif newsgroup == "ab.welovelori":
                            newsgroup = "alt.binaries.welovelori"
                        elif newsgroup == "abblu-ray":
                            newsgroup = "alt.binaries.blu-ray"
                        elif newsgroup == "ab.bloaf":
                            newsgroup = "alt.binaries.bloaf"
                        elif newsgroup == "ab.hdtv.german":
                            newsgroup = "alt.binaries.hdtv.german"
                        elif newsgroup == "abmd":
                            newsgroup = "alt.binaries.movies.divx"
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
                        if int(year) > movieyear + 1 or int(year) < movieyear - 1:
                            continue
        
                    m =  re.search("(.+)\((\d{2}/\d{2}/\d{4})\)", name)
                    dateStr = ""
                    if m:
                        name = m.group(1)
                        dateStr = m.group(2)
                        year = dateStr[-5:].strip(")").strip("/")

                    m =  re.search("(.+)\s+S(\d{2})\s+E(\d{2})(.*)", name)
                    if m:
                        name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)
        
                    m =  re.search("(.+)\s+S(\d{2})\s+Ep(\d{2})(.*)", name)
                    if m:
                        name = m.group(1) + " S" + m.group(2) + "E" + m.group(3) + m.group(4)

                    filenameLower = filename.lower()                                
                    searchItems = []
                    if qualityStr=="":
                        if source in ("Blu Ray-Rip", "HD DVD-Rip"):
                            qualityStr="brrip"
                        elif source =="DVDRip":
                            qualityStr="dvdrip"
                        elif source == "TS":
                            qualityStr ="ts"
                        elif source == "DVDSCR":
                            qualityStr ="scr"
                        elif source == "CAM":
                            qualityStr ="cam"
                        elif moviequality == "dvdr":
                            qualityStr ="dvdr"
                    if year =='':
                        year = '1900'
                    if len(searchItems) == 0 and qualityStr == str(moviequality):
                        searchItems.append( filename )
                    for searchItem in searchItems:
                        resultno=1
                        for downloader in nzbDownloaders:
                            
                            log.info("Searching for download : " + name + ", search string = "+ searchItem + " on " + downloader.__class__.__name__)
                            try:
                                binsearch_result =  downloader.search(searchItem, minSize, newsgroup )
                                if binsearch_result:
                                    new={}
                                    
                                    def extra_check(item):
                                        return True
                                    new['id'] =  binsearch_result.nzbid
                                    new['name'] = name + ' french ' +  qualityStr + ' '+ searchItem +' '+ name +' ' + downloader.__class__.__name__ 
                                    new['url'] = binsearch_result.nzburl
                                    new['detail_url'] = binsearch_result.refererURL
                                    new['size'] = binsearch_result.sizeInMegs
                                    new['age'] = binsearch_result.age
                                    new['extra_check'] = extra_check
        
                                    results.append(new)
                                    
                                    resultno=resultno+1
                                    log.info("Found : " + searchItem + " on " + downloader.__class__.__name__)
                                    if resultno==3:
                                        break
                            except Exception, e:
                                log.error("Searching from " + downloader.__class__.__name__ + " failed : " + str(e) + traceback.format_exc())
    
    def download(self, url = '', nzb_id = ''):
        if 'binsearch' in url:
            params = {'action': 'nzb'}
            params[nzb_id] = 'on'

            try:
                return self.urlopen(url, params = params, show_error = False)
            except:
                log.error('Failed getting nzb from %s: %s', (self.getName(), traceback.format_exc()))
                return 'try_next'
        else:
            values = {
                    'url' : '/'
            }
            data_tmp = urllib.urlencode(values)
            req = urllib2.Request(url, data_tmp )
        
            try:
                #log.error('Failed downloading from %s', self.getName())
                return urllib2.urlopen(req).read()
            except:
                log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

                return 'try_next'
