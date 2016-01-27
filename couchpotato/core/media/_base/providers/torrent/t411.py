from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers.variable import splitString
from datetime import datetime
import json
import re
import traceback

log = CPLog(__name__)


class Base(TorrentProvider):
    
    # urls use by class
    urls = {
        'test': 'http://www.t411.in/',
        'detail': 'http://www.t411.in/torrents/?id=%s',
        'login': 'https://api.t411.in/auth',
        'login_check': 'https://api.t411.in/categories/tree',
        'search': 'https://api.t411.in/torrents/search/%s?cid=%s&offset=0&limit=100',
        'terms_tree': 'https://api.t411.in/terms/tree',
        'download': 'https://api.t411.in/torrents/download/%s',
        }
    # user token 
    token = None
    # api term tree
    apiTermsTree = None
    # arg for getJsonData and openurl : add header "Authorization : Token"
    kwargs = None

    http_time_between_calls = 1 #seconds
    
    #===============================================================================
    # API T411 term ID specifications use in this class :
    # terms[9] :  3D terms
    #    24:3D Converti (Post-Production),
    #    1045:3D Converti (Non officiel/Amateur),
    #    22:2D (Standard),
    #    23:3D Natif (Production),
    # terms[7] : Qualities terms
    #     11:TVrip [Rip SD (non HD) depuis Source HD/SD],
    #     10:DVDrip [Rip depuis DVD-R],
    #     1171:Bluray 4K [Full ou Remux],
    #     1174:Web-Dl 1080,
    #     15:HDrip 720 [Rip HD depuis Bluray],
    #     1162:TVripHD 1080 [Rip HD depuis Source HD],
    #     17:Bluray [Full],
    #     1220:Bluray [Remux],
    #     19:WEBrip,18:VCD/SVCD/VHSrip,
    #     1218:HDlight 720 [Rip HD-leger depuis source HD],
    #     1219:HDrip 4k [Rip HD 4k depuis source 4k],
    #     1182:Web-Dl 4K,
    #     1175:Web-Dl 720,
    #     16:HDrip 1080 [Rip HD depuis Bluray],
    #     1208:HDlight 1080 [Rip HD-leger depuis source HD],
    #     8:BDrip/BRrip [Rip SD (non HD) depuis Bluray ou HDrip],
    #     12:TVripHD 720 [Rip HD depuis Source HD],
    #     13:DVD-R 5 [DVD < 4.37GB],
    #     1233:Web-Dl,
    #     14:DVD-R 9 [DVD > 4.37GB],
    # term[17] : Language terms
    #     1160:Multi (Quebecois inclus),
    #     719:Quebecois (VFQ/French),
    #     542:Multi (Francais inclus),
    #     540:Anglais,
    #     541:Francais (VFF/Truefrench),
    #     722:Muet,
    #     720:VFSTFR,
    #     721:VOSTFR,        
    #===========================================================================    
    # t411 api qualities terms function couchpotato quality identifier
    cat_ids = [
        ([15,1218,1175,12], ['720p']),
        ([1174,1162,16,1208], ['1080p']),
        ([1171,1219,1182], ['2160p']),
        ([13,14], ['dvd-r']),
        ([10], ['dvdrip']),
        ([17,1220], ['br']),
    ]
    # all other qualities if not in cat_ids ( SD qualities )
    default_quality_numbers = [11,19,8,1233,16]
    # getCatId() return this when quality (parameter) is not in catIds
    cat_backup_id = None
    
    # Provide parameters for url to target exact match of movie using
    # quality, movie genre, and french language flag
    # return a tuple ( subCat , terms ) to add to search url
    def getSearchParams(self, movie, quality, frenchLang = None):
        result = {}
        
        # get api terms ( on first time only)
        if not self.apiTermsTree:
            self.apiTermsTree = self.getJsonData(self.urls['terms_tree'], None, **self.kwargs)
        
        # Deal with movie genre
        moviegenre = movie['info']['genres']

        if 'Animation' in moviegenre:
            # Animation
            subcat="455"
        elif 'Documentaire' in moviegenre or 'Documentary' in moviegenre:
            # Documentaire
            subcat="634"
        else:
            # Film    
            subcat="631"
                
        # Deal with quality and 3D Flag
        
        t411_3dquality_numbers = {}       
        if quality['custom']['3d']==1:
            t411_3dquality_numbers.update([(key, value) for key, value in self.apiTermsTree[subcat]["9"]['terms'].iteritems() if (re.search('3d', value, re.IGNORECASE))])
            
        t411_quality_numbers = self.getCatId(quality)
        if not t411_quality_numbers:
            t411_quality_numbers = self.default_quality_numbers
        
        # construct result   
        
        # api subCat
        result['subCat'] = subcat
             
        # api terms for each quality
        terms = ""     
        for qual in t411_quality_numbers:
            terms += '&term[7][]=%s' % qual
        for qual3d in t411_3dquality_numbers.iteritems():
            terms += '&term[9][]=%s' % qual3d[0]

        # api term for french language
        if frenchLang:
            t411_french_language_numbers = [719,1160,542,541]
            for lang in t411_french_language_numbers:
                terms += '&term[17][]=%s' % lang
                
        result['terms'] = terms
        
        return result
    
    # call to search a movie
    # return movie search results
    def _searchOnTitle(self, title, movie, quality, results):
        
        log.debug('t411 : SearchOnTitle title: "%s"' % title)
        
        # if required words in settings contains 'french', use french flag with getSearchParams()
        required_words = splitString(self.conf('required_words', section = 'searcher').lower())
        frenchFlag = False
        if 'french' in required_words:
            frenchFlag = True
        # get more precise params function quality genre and frenchFlag
        params = self.getSearchParams(movie, quality, frenchFlag)
        
        # to deal with french title and encoding, we smplify the string
        # t411 dont take care of accent of title so simplifyString(title)
        url = self.urls['search'] % ( tryUrlencode('%s %s' % (simplifyString(title), movie['info']['year'])), params['subCat']) + params['terms']
        

        log.debug('t411 : SearchOnTitle URL : %s' % url)
        
        # search call 
        data = self.getJsonData(url, None, **self.kwargs)
        if data:
            if 'torrents' in data:
                for torrent in data['torrents']:
                    # for couchpotato detection
                    # we replace and add some info in the torrent name
                    # suppress all '(...)' because can be a problem for couchpotato name detection
                    newTitle = re.sub('\(.*\)','', torrent['name'])
                    # add frenchFlag + label quality to be sure couchpotato recognize quality
                    namesuffix =(' french ' if frenchFlag else ' ') + quality['label']
                    # convert size
                    size =  torrent['size']
                    sizeint = tryInt(size, 0) / 1024  # Kb
                    results.append({
                                'id': torrent['id'],
                                'name': newTitle + namesuffix,
                                'url': self.urls['download'] % torrent['id'],
                                'detail_url': self.urls['detail'] % torrent['id'],
                                'size': self.parseSize(str(sizeint) + ' kb'),
                                'seeders': tryInt(torrent['seeders']),
                                'leechers': tryInt(torrent['leechers']),
                                'age': self.addedTimeToDays(torrent['added'])
                            })
                    log.debug('t411 : SearchOnTitle Found : %s' % torrent['name'])
            if 'total' in data:
                log.debug('t411 : SearchOnTitle Total Found : %s' % data['total'])
        else:
            log.warning('t411 : SearchOnTitle data result is empty!!!')

    # convert time string to age in days
    def addedTimeToDays(self, addedTime):
        try:
            addedDate = datetime.strptime(addedTime,"%Y-%m-%d %H:%M:%S")
            age = addedDate - datetime.now()
            return abs(age.days)
        except ValueError :
            return 0
        
    def getLoginParams(self):
        return { 
                'username': self.conf('username'),
                'password': self.conf('password'),
        }
    
    def loginSuccess(self, output):
        jsonOutput = json.loads(output)
        if 'token' in jsonOutput:
            self.token = jsonOutput['token']
            self.kwargs = {
                'headers': {'Authorization' : self.token }
                 }
            return True
        else:
            return False

    loginCheckSuccess = loginSuccess
    
    # execute login if necessary + download with authentication
    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login():
                log.error('Failed login when downloading from %s', self.getName())
            return self.urlopen(url, **self.kwargs)
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))
    

config = [{
    'name': 't411',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 't411',
            'description': 'See <a href="https://www.t411.in/">T411</a>',
            'icon' : 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAA3NCSVQICAjb4U/gAAACdklEQVQokW2RX0hTcRTHz+/+cbvz3m1srbv8M6Ws6SbK1hRTkUoKIui5jIJ8sz9vQQTRQxDRexCkIGgmSC+B1YNWNCIrRQ3Z2PyTf5pb2/S2ud2/2723hyIt/b4cDud7+H4OB2CXrpOW+wYLYPju0R66DTABEAWYB7i6lwHtbEYAKi5crPE36Wa6QGKQyYylk1cePPwX4FqPquSSiZVHAN+Gh/JihpezUpGXinmxkBN5Lvjm5U4/1hzwS5JsJIkzkWnmZDtSZF2WQZZ0SSoIgiSJXq+37VjLNhLL7h/ofUzg0Dceutl1ejHOoa0fScUQW1rouXQWw3ANULXbt8cNJ7pudPrcd/pmLp8PBNpa344HDYTqYc2Ls58G+59sI/0uTgBTKj78OQIdTb6W5gKg+PpKaPprUoLB/mBHY/v/CacARru7ucaG6NCrj5vp2rpDWvmBDa83PzDwdJVOl5Zo8S+JQhoD7E/CGMBEKLyYTNWjLKNl6KkP5OsXbE1leGqdNFoBd3K034jbcJzYfqfPTpUZjOHkmkmS+SpzinXYlxdGM+4I5ezkoyHSUcIjHXHY3wWPqM9SOg2ataFMlvQ6YWs5FIvaKxxgmzEfrWYOazanXuAxAGBwGALoNcWePxtx8cKR4wGuBFZo05TI2gXViE3SaiyVn3bQRgU0DABuVdHn7na6iuSMAOk2X6WnrqLcMVlqTVQ5lHw2VaQURtNN+7YoD7L4cQCQKGo9GJsUEGC6bNPfzc1xpZAjWuH7+3u+xHy+BuFLLkYsx7la0yrCAeqdZg0h1kDQFkpVlSyvrG1krM5mNbtK/9wM0wddjF6UNywElpWVX6HUDxDMdBkmAAAAAElFTkSuQmCC',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
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
                },
            ],
        },
    ],
}]
    