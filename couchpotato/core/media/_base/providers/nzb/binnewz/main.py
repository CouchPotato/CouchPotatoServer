from binsearch import BinSearch
from nzbclub import NZBClub
from nzbindex import NZBIndex

from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, splitString, tryInt
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.environment import Env
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers import namer_check
from couchpotato.core.media._base.providers.nzb.base import NZBProvider

log = CPLog(__name__)
import re
import urllib
import urllib2
import traceback
class Base(NZBProvider):
    
    urls = {
        'download': 'http://www.binnews.in/',
        'detail': 'http://www.binnews.in/',
        'search': 'http://www.binnews.in/_bin/search2.php',
    }

    http_time_between_calls = 4 # Seconds
    cat_backup_id = None
    
    def _search(self, movie, quality, results):
        nzbDownloaders = [NZBClub(), BinSearch(), NZBIndex()]
        MovieTitles = movie['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        movieyear = movie['info']['year']
        if quality['custom']['3d']==1:
            threeD= True
        else:
            threeD=False
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
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                continue
            if threeD:
                TitleStringReal = TitleStringReal + ' 3d'
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
                    
                    detectedlang=''
                    
                    if "_fr" in language:
                        detectedlang=' truefrench '
                    else:
                        detectedlang=' french '
                                                    
      
                    # blacklist_groups = [ "alt.binaries.multimedia" ]
                    blacklist_groups = []                
                    
                    newgroupLink = cells[4].find("a")
                    newsgroup = None
                    if newgroupLink.contents:
                        newsgroup = newgroupLink.contents[0]
                        if newsgroup == "abmulti":
                            newsgroup = "alt.binaries.multimedia"
                        elif newsgroup == "ab.moovee":
                            newsgroup = "alt.binaries.moovee"
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
                        elif newsgroup == "ab.ath":
                            newsgroup = "alt.binaries.ath"
                        elif newsgroup == "a.b.town":
                            newsgroup = "alt.binaries.town"
                        elif newsgroup == "a.b.u-4all":
                            newsgroup = "alt.binaries.u-4all"
                        elif newsgroup == "ab.amazing":
                            newsgroup = "alt.binaries.amazing"
                        elif newsgroup == "ab.astronomy":
                            newsgroup = "alt.binaries.astronomy"
                        elif newsgroup == "ab.nospam.cheer":
                            newsgroup = "alt.binaries.nospam.cheerleaders"
                        elif newsgroup == "ab.worms":
                            newsgroup = "alt.binaries.worms"
                        elif newsgroup == "abcores":
                            newsgroup = "alt.binaries.cores"
                        elif newsgroup == "abdvdclassics":
                            newsgroup = "alt.binaries.dvd.classics"
                        elif newsgroup == "abdvdf":
                            newsgroup = "alt.binaries.dvd.french"
                        elif newsgroup == "abdvds":
                            newsgroup = "alt.binaries.dvds"
                        elif newsgroup == "abmdfrance":
                            newsgroup = "alt.binaries.movies.divx.france"
                        elif newsgroup == "abmisc":
                            newsgroup = "alt.binaries.misc"
                        elif newsgroup == "abnl":
                            newsgroup = "alt.binaries.nl"
                        elif newsgroup == "abx":
                            newsgroup = "alt.binaries.x"
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
                                    qualitytag=''
                                    if qualityStr.lower() in ['720p','1080p']:
                                        qualitytag=' hd x264 h264 '
                                    elif qualityStr.lower() in ['dvdrip']:
                                        qualitytag=' dvd xvid '
                                    elif qualityStr.lower() in ['brrip']:
                                        qualitytag=' hdrip '
                                    elif qualityStr.lower() in ['ts']:
                                        qualitytag=' webrip '
                                    elif qualityStr.lower() in ['scr']:
                                        qualitytag=''
                                    elif qualityStr.lower() in ['dvdr']:
                                        qualitytag=' pal video_ts '
                                    new['id'] =  binsearch_result.nzbid
                                    new['name'] = name + detectedlang +  qualityStr + qualitytag + downloader.__class__.__name__ 
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
            data = {
            'action': 'nzb',
            nzb_id: 'on'
            }
            try:
                return self.urlopen(url, data = data, show_error = False)
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
config = [{
    'name': 'binnewz',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'nzb_providers',
            'name': 'binnewz',
            'description': 'Free provider, lots of french nzbs. See <a href="http://www.binnews.in/">binnewz</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAgRJREFUOI1t009rVFcYx/HPuffOTGYmMcZoEmNUkiJRSZRAC1ropuimuy6KuHHhShe+EF+CL8AX4LpQCgoiohhMMKKMqHRTtaJJ5k8nudfFnBkjzoEf5zk8PN/zO3+egFGMYX+MS9hFG604d/A/ulG7yFFkqOGgcuUuSJK32q0NPMMaNrE9RC10UxzCedX6767cqDu2MGV8YlFz62ed9iWVkYvy/IyimEUSFaKD3QwV7ENwapmlHymVU5126tNHVh9MW3s8bfXhOW8b16TpliR5otW8jm6GHiSEYOYoF076Zjx6x29/8OHfssZzNp6Ou3XzF8zicxYtZWBislfUKL4CFgIvd5mcYuowed7PjKOSGTYWwiAsij6srChmJI058Q6qyIYD9jgIIQzWxXygPtZPpUj6gGJv/V4HGoViPsLWt77bK9P7FDtg8zPr21RrX48wT3g11OcA0MG2oii8aXB4jiInK5FmSAcOGBUawwFvtFuJO7dpbLBynuM/UK0Jn0YolXtqNfn4vl/bRZ7pfcsXdrqX3f/rhgd/L+m0J8zMdZ1eKTn7U7C4zNg+yhX+ed2/syZ2AkZQ12umSRyI8wpOqdaXdTszRmocOR5Mz2bu/ZnL81/xIsTnyFCOsKpeg9ViPBo1jxMq1UVpEjS3r+K/Pe81aJQ0qhShlQiuxPxOtL+J1heOZZ0e63LUQAAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
