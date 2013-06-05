from xml.dom.minidom import parseString
from xml.dom.minidom import Node
import cookielib
import urllib
import urllib2
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, mergeDicts
from couchpotato.core.providers.torrent.base import TorrentProvider
from dateutil.parser import parse

from couchpotato.core.event import fireEvent

log = CPLog(__name__)

class gks(TorrentProvider):

    urls = {
        'test': 'https://gks.gs/',
        'search': 'https://gks.gs/',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None
     
    def getSearchParams(self, movie, quality):
        results = []
        MovieTitles = movie['library']['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        movieyear = movie['library']['year']
        for MovieTitle in MovieTitles:
            TitleStringReal = str(MovieTitle.encode("utf-8").replace('-',' '))
            if moviequality in ['720p']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 15, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            elif moviequality in ['1080p']:
                 results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 16, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            elif moviequality in ['dvd-r']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 19, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            elif moviequality in ['br-disk']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 17, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            else:
                 results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 5, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
        return results
                   
    def _search(self, movie, quality, results):
        searchStrings= self.getSearchParams(movie,quality)
        for searchString in searchStrings:
            searchUrl = self.urls['search']+'rdirect.php?type=search&'+searchString
            log.info(u"Search URL: " + searchUrl)
            
            data = self.getHTMLData(searchUrl)
            if "bad key" in str(data).lower() :
                log.error(u"GKS key invalid, check your config")
                continue
    
            parsedXML = parseString(data)
            channel = parsedXML.getElementsByTagName('channel')[0]
            description = channel.getElementsByTagName('description')[0]
            #description_text = self.get_xml_text(description).lower()
            text = ""
            for child_node in description.childNodes:
                if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                    text += child_node.data
            description_text=text.strip().lower()
            
            if "user can't be found" in description_text:
                log.error(u"GKS invalid digest, check your config")
                continue
            elif "invalid hash" in description_text:
                log.error(u"GKS invalid hash, check your config")
                continue
            else :
                items = channel.getElementsByTagName('item')
                for item in items:
                    text = ""
                    for child_node in item.getElementsByTagName('title')[0].childNodes:
                        if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                            text += child_node.data
                    title=text.strip().lower()
                                        
                    if "aucun resultat" in title.lower() :
                        log.info(u"No results found in " + searchUrl)
                        continue
                    else :
                        
                        #MovieTitles = movie['library']['info']['titles']
                        #testname=0
                        #for movietitle in MovieTitles:
                        #    testname += self.correctName(title,movietitle)
                        #if testname==0:
                        #    continue
                        text = ""
                        for child_node in item.getElementsByTagName('link')[0].childNodes:
                            if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                                text += child_node.data
                        downloadURL=text.strip().lower()
                        desc=""
                        for child_node in item.getElementsByTagName('description')[0].childNodes:
                            if child_node.nodeType in (Node.CDATA_SECTION_NODE, Node.TEXT_NODE):
                                desc += child_node.data
                        desc=desc.strip().lower()
                        desc_values=desc.split(" | ")
                        dict_attr={}
                        for x in desc_values:
                            x_values=x.split(" : ")
                            dict_attr[x_values[0]]=x_values[1]
                        date=""
                        size=""
                        leechers=""
                        seeders=""
                        if "ajoute le" in dict_attr:
                            date=dict_attr["ajoute le"]
                        if "taille" in dict_attr:
                            size=dict_attr["taille"]
                        if "seeders" in dict_attr:
                            seeders=dict_attr["seeders"]
                        if "leechers" in dict_attr:
                            leechers=dict_attr["leechers"]
                        def extra_check(item):
                                return True
                            
                        new = {}
                        new['id'] = title
                        new['name'] = title.strip()
                        new['url'] = downloadURL
                        new['detail_url'] = searchUrl
                           
                        new['size'] = self.parseSize(size)
                        new['age'] = self.ageToDays(date)
                        new['seeders'] = tryInt(seeders)
                        new['leechers'] = tryInt(leechers)
                        new['extra_check'] = extra_check
                        results.append(new)
              
    def _get_title_and_url(self, item):
        return (item.title, item.url)
    
    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')
        age_str = age_str[:10]
        date=datetime.strptime(age_str,'%Y-%m-%d')
        delta=abs((datetime.now() - date).days)

        return tryInt(delta)
    
    def correctName(self, check_name, movie_name):

        check_names = [check_name]

        # Match names between "
        try: check_names.append(re.search(r'([\'"])[^\1]*\1', check_name).group(0))
        except: pass

        # Match longest name between []
        try: check_names.append(max(check_name.split('['), key = len))
        except: pass

        for check_name in list(set(check_names)):
            check_movie = fireEvent('scanner.name_year', check_name, single = True)

            try:
                check_words = filter(None, re.split('\W+', check_movie.get('name', '')))
                movie_words = filter(None, re.split('\W+', simplifyString(movie_name)))

                if len(check_words) > 0 and len(movie_words) > 0 and len(list(set(check_words) - set(movie_words))) == 0:
                    return 1
            except:
                pass

        return 0
    
    def download(self, url = '', nzb_id = ''):
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
 