from xml.dom.minidom import parseString
from xml.dom.minidom import Node
import urllib
import urllib2
from datetime import datetime
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers import namer_check
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import traceback

log = CPLog(__name__)

class Base(TorrentProvider):

    urls = {
        'test': 'https://gks.gs/',
        'search': 'https://gks.gs/',
    }
    
    http_time_between_calls = 1 #seconds
    cat_backup_id = None
     
    def getSearchParams(self, movie, quality):
        results = []
        MovieTitles = movie['info']['titles']
        moviequality = simplifyString(quality['identifier'])
        for MovieTitle in MovieTitles:
            try:
                TitleStringReal = str(MovieTitle.encode("latin-1").replace('-',' '))
            except:
                continue
            if moviequality in ['720p']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 15, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
                results.append( urllib.urlencode( {'q': simplifyString(TitleStringReal), 'category' : 15, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
            elif moviequality in ['1080p']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 16, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
                results.append( urllib.urlencode( {'q': simplifyString(TitleStringReal), 'category' : 16, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
            elif moviequality in ['dvd-r']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 19, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
                results.append( urllib.urlencode( {'q': simplifyString(TitleStringReal), 'category' : 19, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
            elif moviequality in ['br-disk']:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 17, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
                results.append( urllib.urlencode( {'q': simplifyString(TitleStringReal), 'category' : 17, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
            else:
                results.append( urllib.urlencode( {'q': TitleStringReal, 'category' : 5, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
                results.append( urllib.urlencode( {'q': simplifyString(TitleStringReal), 'category' : 5, 'ak' : self.conf('userkey')} ) + "&order=desc&sort=normal&exact" )
            
        return results
                   
    def _search(self, movie, quality, results):
        searchStrings= self.getSearchParams(movie,quality)
        for searchString in searchStrings:
            searchUrl = self.urls['search']+'rdirect.php?type=search&'+searchString
                        
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
                        log.debug("No results found trying another if there is one")
                        continue
                    else :
                        testname=namer_check.correctName(title,movie)
                        if testname==0:
                            continue
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
config = [{
    'name': 'gks',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'gks',
            'description': 'See <a href="https://gks.gs/">Gks</a>',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'userkey',
                    'label': 'Authentification key',
                    'default': '',
                },
                        {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
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
 