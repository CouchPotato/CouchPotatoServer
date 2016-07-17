import re
import traceback
import random
from datetime import datetime

from couchpotato import fireEvent
from couchpotato.core.helpers.variable import tryInt, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentMagnetProvider

log = CPLog(__name__)

class Base(TorrentMagnetProvider):

    urls = {
        'test': 'https://torrentapi.org/pubapi_v2.php?app_id=couchpotato',
        'token': 'https://torrentapi.org/pubapi_v2.php?get_token=get_token&app_id=couchpotato',
        'search': 'https://torrentapi.org/pubapi_v2.php?token=%s&mode=search&search_imdb=%s&min_seeders=%s&min_leechers'
                  '=%s&ranked=%s&category=movies&format=json_extended&app_id=couchpotato',
    }

    http_time_between_calls = 2  # Seconds
    _token = 0

    def _search(self, movie, quality, results):
        hasresults = 0
        curryear = datetime.now().year
        movieid = getIdentifier(movie)

        try:
            movieyear = movie['info']['year']
        except:
            log.error('RARBG: Couldn\'t get movie year')
            movieyear = 0

        self.getToken()

        if (self._token != 0) and (movieyear == 0 or movieyear <= curryear):
            data = self.getJsonData(self.urls['search'] % (self._token, movieid, self.conf('min_seeders'),
                                                           self.conf('min_leechers'), self.conf('ranked_only')), headers = self.getRequestHeaders())

            if data:
                if 'error_code' in data:
                    if data['error'] == 'No results found':
                        log.debug('RARBG: No results returned from Rarbg')
                    else:
                        if data['error_code'] == 10:
                            log.error(data['error'], movieid)
                        else:
                            log.error('RARBG: There is an error in the returned JSON: %s', data['error'])
                else:
                    hasresults = 1

                try:
                    if hasresults:
                        for result in data['torrent_results']:
                            name = result['title']
                            titlesplit = re.split('-', name)
                            releasegroup = titlesplit[len(titlesplit)-1]

                            xtrainfo = self.find_info(name)
                            encoding = xtrainfo[0]
                            resolution = xtrainfo[1]
                            # source = xtrainfo[2]
                            pubdate = result['pubdate']  # .strip(' +0000')
                            try:
                                pubdate = datetime.strptime(pubdate, '%Y-%m-%d %H:%M:%S +0000')
                                now = datetime.utcnow()
                                age = (now - pubdate).days
                            except ValueError:
                                log.debug('RARBG: Bad pubdate')
                                age = 0

                            torrentscore = self.conf('extra_score')
                            seeders = tryInt(result['seeders'])
                            torrent_desc = '/ %s / %s / %s / %s seeders' % (releasegroup, resolution, encoding, seeders)

                            if seeders == 0:
                                torrentscore = 0

                            sliceyear = result['pubdate'][0:4]
                            year = tryInt(sliceyear)

                            results.append({
                                'id': random.randint(100, 9999),
                                'name': re.sub('[^A-Za-z0-9\-_ \(\).]+', '', '%s (%s) %s' % (name, year, torrent_desc)),
                                'url': result['download'],
                                'detail_url': result['info_page'],
                                'size': tryInt(result['size']/1048576),  # rarbg sends in bytes
                                'seeders': tryInt(result['seeders']),
                                'leechers': tryInt(result['leechers']),
                                'age': tryInt(age),
                                'score': torrentscore
                            })

                except RuntimeError:
                    log.error('RARBG: Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getToken(self):
        tokendata = self.getJsonData(self.urls['token'], cache_timeout = 900, headers = self.getRequestHeaders())
        if tokendata:
            try:
                token = tokendata['token']
                if self._token != token:
                    log.debug('RARBG: GOT TOKEN: %s', token)
                self._token = token
            except:
                log.error('RARBG: Failed getting token from Rarbg: %s', traceback.format_exc())
                self._token = 0

    def getRequestHeaders(self):
        return {
            'User-Agent': fireEvent('app.version', single = True)
        }

    @staticmethod
    def find_info(filename):
        # CODEC #
        codec = 'x264'
        v = re.search('(?i)(x265|h265|h\.265)', filename)
        if v:
            codec = 'x265'

        v = re.search('(?i)(xvid)', filename)
        if v:
            codec = 'xvid'

        # RESOLUTION #
        resolution = 'SD'
        a = re.search('(?i)(720p)', filename)
        if a:
            resolution = '720p'

        a = re.search('(?i)(1080p)', filename)
        if a:
            resolution = '1080p'

        a = re.search('(?i)(2160p)', filename)
        if a:
            resolution = '2160p'

        # SOURCE #
        source = 'HD-Rip'
        s = re.search('(?i)(WEB-DL|WEB_DL|WEB\.DL)', filename)
        if s:
            source = 'WEB-DL'

        s = re.search('(?i)(WEBRIP)', filename)
        if s:
            source = 'WEBRIP'

        s = re.search('(?i)(DVDR|DVDRip|DVD-Rip)', filename)
        if s:
            source = 'DVD-R'

        s = re.search('(?i)(BRRIP|BDRIP|BluRay)', filename)
        if s:
            source = 'BR-Rip'

        s = re.search('(?i)BluRay(.*)REMUX', filename)
        if s:
            source = 'BluRay-Remux'

        s = re.search('(?i)BluRay(.*)\.(AVC|VC-1)\.', filename)
        if s:
            source = 'BluRay-Full'

        return_info = [codec, resolution, source]
        return return_info

config = [{
    'name': 'rarbg',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'RARBG',
            'wizard': True,
            'description': '<a href="https://rarbg.to/torrents.php" target="_blank">RARBG</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAB+UlEQVQ4jYXTP2hcRxDH8c8JJZjbYNy8V7gIr0qhg5AiFnETX'
                    '+PmVAtSmKDaUhUiFyGxjXFlp0hhHy5cqFd9lSGcU55cBU6EEMIj5dsmMewSjNGmOJ3852wysMyww37n94OdXimlh49xDR/hxGr'
                    '8hZ/xx0qnlHK5lPKk/H/8U0r5oZTyQSmltzzr+AKfT+ed8UFLeHNAH1UVbA2r88NBfQcX8O2yv74sUqKNWT+T01sy2+zpUbS/w'
                    '/awvo7H+O0NQEA/LPKlQWXrSgUmR9HxcZQwmbZGw/pc4MsVAIT+IjcNw80aTjaaem1vPCNlGakj1C6uWFiqeDtyTvoyqAKhBn+'
                    '+E7CkxC6Zzjop57XpUSenpIuMhpXAc/zyHkAicRSjw6fHZ1ewPdqwszWAB2hXACln8+NWSlld9zX9YN7GhajQXz5+joPXR66de'
                    'U1J27Zi7FzaqE0OdmwNGzF2Ymzt3j+E8/gJH64AFlozKS4+Be7tjwyaIKVsOpnavX0II9x8ByDLKco5SwvjL0MI/z64tyOcwsf'
                    'jQw8PJvAdvsb6GSBlxI7UyTnD37i7OWhe3NrflvOit3djbDKdwR181SulXMXdrkubbdvKaOpK09S/4jP8iG9m8zmJjCoEg0HzO'
                    '77vna7zp7ju1TqfYIyZxT7dwCd4eWr7BR7h2X8S6gShJlbKYQAAAABJRU5ErkJggg==',
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
                    'description': 'Only ranked torrents (internal), scene releases, rarbg releases. '
                                   'Enter 1 (true) or 0 (false)',
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
