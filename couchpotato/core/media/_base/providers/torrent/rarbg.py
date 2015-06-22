import re
import traceback
import random
from datetime import datetime

from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider

log = CPLog(__name__)
token = '0'
class Base(TorrentMagnetProvider):

    urls = {
        'test': 'https://torrentapi.org/pubapi_v2.php',
        'token': 'https://torrentapi.org/pubapi_v2.php?get_token=get_token',
        'search': 'https://torrentapi.org/pubapi_v2.php?token=%s&mode=search&search_imdb=%s&min_seeders=%s&min_leechers=%s&ranked=%s&category=movies&format=json_extended',
    }
    
    http_time_between_calls = 2  # Seconds
    
    def find_info(foo,filename):
        # CODEC #
        codec = 'x264'
        v = re.search("(?i)(x265|h265|h\.265)",filename)
        if v:
            codec = 'x265'
        
        v = re.search("(?i)(xvid)",filename)
        if v:
            codec = 'xvid'

        # RESOLUTION #
        resolution = 'SD'            
        a = re.search("(?i)(720p)",filename)
        if a:
            resolution = '720p'
            
        a = re.search("(?i)(1080p)",filename)
        if a:
            resolution = '1080p'
            
        a = re.search("(?i)(2160p)",filename)
        if a:
            resolution = '2160p'

        # SOURCE #
        source = 'HD-Rip'            
        s = re.search("(?i)(WEB-DL|WEB_DL|WEB\.DL)",filename)
        if s:
            source = 'WEB-DL'
            
        s = re.search("(?i)(WEBRIP)",filename)
        if s:
            source = 'WEBRIP'

        s = re.search("(?i)(DVDR|DVDRip|DVD-Rip)",filename)
        if s:
            source = 'DVD-R'

        s = re.search("(?i)(BRRIP|BDRIP|BluRay)",filename)
        if s:
            source = 'BR-Rip'
            
        s = re.search("(?i)BluRay(.*)REMUX",filename)
        if s:
            source = 'BluRay-Remux'
            
        s = re.search("(?i)BluRay(.*)\.(AVC|VC-1)\.",filename)
        if s:
            source = 'BluRay-Full'
            
        return_info = []
        return_info.append(codec);
        return_info.append(resolution);
        return_info.append(source);
        return return_info;

    def _search(self, movie, quality, results):
        log.debug("getting rarbg token")
        global token
        tokendata = self.getJsonData(self.urls['token'])

        if tokendata:
            try:
                token = tokendata['token']
                log.debug("GOT TOKEN: %s", token)
            except:
                log.error('Failed getting token from rarbg')

        if token != '0':      
            data = self.getJsonData(self.urls['search'] % (token, getIdentifier(movie), self.conf('min_seeders'), self.conf('min_leechers'), self.conf('ranked_only')))

            if data:
                if 'error_code' in data:
                    raise ValueError("There is an error in the returned JSON")
                    log.error(data['error'])
                try:
                    for result in data['torrent_results']:
                        age = 0
                        name = result['title']
                        titlesplit = re.split("-",name)
                        releasegroup = titlesplit[len(titlesplit)-1]
                        
                        xtrainfo = self.find_info(name)
                        encoding = xtrainfo[0]
                        resolution = xtrainfo[1]
                        source = xtrainfo[2]
                        pubdate = result['pubdate'].strip(" +0000")
                        try:
                            pubdate = datetime.strptime(pubdate, '%Y-%m-%d %H:%M:%S')
                            now = datetime.utcnow()
                            age = now - pubdate
                        except:
                            log.debug("Bad pubdate")

                        torrentscore = self.conf('extra_score')
                        seeders = tryInt(result['seeders'])
                        torrent_desc = '/ %s / %s / %s / %s seeders' % (releasegroup, resolution, encoding, seeders)

                        if seeders == 0:
                            torrentscore = 0
                        
                        sliceyear = result['pubdate'][0:4]
                        year = tryInt(sliceyear)

                        results.append({
                            'id': tryInt(random.random()),
                            'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                            'url': result['download'],
                            'detail_url': result['info_page'],
                            'size': tryInt(result['size']/1048576), #rarbg sends in bytes
                            'seeders': tryInt(result['seeders']),
                            'leechers': tryInt(result['leechers']),
                            'age': tryInt(age),
                            'score': torrentscore
                        })
                except:
                    log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
config = [{
    'name': 'rarbg',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'Rarbg',
            'wizard': True,
            'description': '<a href="https://rarbg.to/torrents.php">RARBG</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAB+UlEQVQ4jYXTP2hcRxDH8c8JJZjbYNy8V7gIr0qhg5AiFnETX+PmVAtSmKDaUhUiFyGxjXFlp0hhHy5cqFd9lSGcU55cBU6EEMIj5dsmMewSjNGmOJ3852wysMyww37n94OdXimlh49xDR/hxGr8hZ/xx0qnlHK5lPKk/H/8U0r5oZTyQSmltzzr+AKfT+ed8UFLeHNAH1UVbA2r88NBfQcX8O2yv74sUqKNWT+T01sy2+zpUbS/w/awvo7H+O0NQEA/LPKlQWXrSgUmR9HxcZQwmbZGw/pc4MsVAIT+IjcNw80aTjaaem1vPCNlGakj1C6uWFiqeDtyTvoyqAKhBn++E7CkxC6Zzjop57XpUSenpIuMhpXAc/zyHkAicRSjw6fHZ1ewPdqwszWAB2hXACln8+NWSlld9zX9YN7GhajQXz5+joPXR66deU1J27Zi7FzaqE0OdmwNGzF2Ymzt3j+E8/gJH64AFlozKS4+Be7tjwyaIKVsOpnavX0II9x8ByDLKco5SwvjL0MI/z64tyOcwsfjQw8PJvAdvsb6GSBlxI7UyTnD37i7OWhe3NrflvOit3djbDKdwR181SulXMXdrkubbdvKaOpK09S/4jP8iG9m8zmJjCoEg0HzO77vna7zp7ju1TqfYIyZxT7dwCd4eWr7BR7h2X8S6gShJlbKYQAAAABJRU5ErkJggg==',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                {
                    'name': 'ranked_only',
                    'advanced': True,
                    'label': 'Ranked Only',
                    'type': 'int',
                    'default': 1,
                    'description': 'Only ranked torrents (internal), scene releases + -rarbg releases. Enter 1 (true) or 0 (false)',
                },
                {
                    'name': 'min_seeders',
                    'advanced': True,
                    'label': 'Minimum Seeders',
                    'type': 'int',
                    'default': 10,
                    'description': 'Minium amount of seeders the release must have.',
                }, 
                {
                    'name': 'min_leechers',
                    'advanced': True,
                    'label': 'Minimum leechers',
                    'type': 'int',
                    'default': 0,
                    'description': 'Minium amount of leechers the release must have.',
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
