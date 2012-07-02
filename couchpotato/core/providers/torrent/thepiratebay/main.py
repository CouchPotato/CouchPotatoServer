#!/usr/bin/python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import re
from urllib import quote_plus
import urllib2
log = CPLog(__name__)


class ThePirateBay(TorrentProvider):

    cat_ids = [([207], ['720p', '1080p']), ([201], [
        'cam',
        'ts',
        'dvdrip',
        'tc',
        'r5',
        'scr',
        'brrip',
        ]), ([202], ['dvdr'])]

    cat_backup_id = 200

    def __init__(self):
        super(ThePirateBay, self).__init__()
        self.urls = {"test": self.getAPIurl(), 'detail': '%s/torrent/%s', 'search': '%s/search/%s/0/7/%d'}

    def getAPIurl(self, url=""):
        return (("http://thepiratebay.se", self.conf('domain_for_tpb'))[self.conf('domain_for_tpb') != None]) + url

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        movie_name = re.sub("\W", ' ', getTitle(movie['library']))
        movie_name = re.sub('  ', ' ', movie_name)

        log.info('API url: %s', self.getAPIurl())
        log.info('Cleaned Name: %s', movie_name)

        cache_key = 'thepiratebay.%s.%s' % (movie['library'
                ]['identifier'], quality.get('identifier'))
        searchUrl = self.urls['search'] % (self.getAPIurl(),
                quote_plus(movie_name + ' ' + quality['identifier']),
                self.getCatId(quality['identifier'])[0])
        log.info('searchUrl: %s', searchUrl)
        data = self.getCache(cache_key, searchUrl)
        #print data
        if not data:
            log.error('Failed to get data from %s.', searchUrl)
            return results

        try:
            soup = BeautifulSoup(data)
            resultsTable = soup.find('table',
                    attrs={'id': 'searchResult'})
            entries = resultsTable.findAll('tr')
            for result in entries[1:]:
                link = result.find(href=re.compile('torrent\/\d+\/'))
                download = result.find(href=re.compile('magnet:'))
                #Uploaded 06-28 02:27, Size 1.37 GiB,
                size = re.search('Size (?P<size>.+),', unicode(result.select("font.detDesc")[0])).group("size")
                if link and download:
                    new = {
                        'type': 'magnet',
                        'check_nzb': False,
                        'description': '',
                        'provider': self.getName(),
                        }

                    trusted = (0, 10)[result.find('img',
                            alt=re.compile('Trusted')) != None]
                    vip = (0, 20)[result.find('img',
                                  alt=re.compile('VIP')) != None]
                    moderated = (0, 50)[result.find('img',
                            alt=re.compile('Moderator')) != None]

                    log.info('Name: %s', link.string)
                    log.info('Seeders: %s', result.findAll('td'
                             )[2].string)
                    log.info('Leechers: %s', result.findAll('td'
                             )[3].string)
                    log.info('Size: %s', size)
                    log.info('Score(trusted + vip + moderated): %d',
                             trusted + vip + moderated)

                    new['name'] = link.string
                    new['id'] = re.search('/(?P<id>\d+)/', link['href'
                            ]).group('id')
                    new['url'] = self.getAPIurl(link['href'])
                    new['magnet'] = unicode(download['href'])  # forcing of storing full magnet data
                    new['size'] = self.parseSize(size)
                    new['seeders'] = int(result.findAll('td')[2].string)
                    new['leechers'] = int(result.findAll('td'
                            )[3].string)

                    new['TPB_score'] = trusted + vip + moderated
                    new['extra_score'] = self.extra_score
                    new['score'] = fireEvent('score.calculate', new,
                            movie, single=True)

                    isImdb = self.imdbMatch(self.getAPIurl(link['href']), movie['library']['identifier'])

                    is_correct_movie = fireEvent(
                        'searcher.correct_movie',
                        nzb=new,
                        movie=movie,
                        quality=quality,
                        imdb_results=isImdb,
                        single_category=False,
                        single=True,
                        )

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

            return results
        except Exception, e:
            log.debug(e)
            log.info('Error occured during parsing! Passing only processed entries'
                     )
            return results

    def extra_score(self, torrent):
        return torrent["TPB_score"]

    def imdbMatch(self, url, imdbId):
        log.info('imdbMatch: %s', url)
        try:
            data = urllib2.urlopen(url).read()
            pass
        except:
            log.error('Failed to open %s.' % url)
            return False
        imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)
        data = unicode(data, errors='ignore')
        if 'imdb.com/title/' + imdbId in data or 'imdb.com/title/' \
            + imdbIdAlt in data:
            return True
        return False

    def download(self, url='', nzb_id=''):
        return url
