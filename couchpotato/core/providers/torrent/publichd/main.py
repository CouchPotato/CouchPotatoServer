#!/usr/bin/python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
import re
from urlparse import parse_qs
from urllib import quote_plus
import urllib2
log = CPLog(__name__)


class PublicHD(TorrentProvider):

    urls = {
        'test': 'http://publichd.eu',
        'download': 'http://publichd.eu/%s',
        'detail': 'http://publichd.eu/index.php?page=torrent-details&id=%s',
        'search': 'http://publichd.eu/index.php?page=torrents&search=%s&active=1&category=%d',
        }

    cat_ids = [([2], ['720p']), ([5], ['1080p']), ([15], ['bdrip']),
               ([16], ['brrip']), ([16], ['blue-ray'])]

    cat_backup_id = 0

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        movie_name = re.sub("\W", " ", getTitle(movie['library']))
        movie_name = re.sub("  ", " ", movie_name)
        log.info('Cleaned Name: %s', movie_name)
        cache_key = 'publichd.%s.%s' % (movie['library']['identifier'], quality.get('identifier'))
        searchUrl = self.urls['search'] \
            % (quote_plus(movie_name + ' '
               + quality['identifier']),
               self.getCatId(quality['identifier'])[0])
        log.info('searchUrl: %s', searchUrl)
        data = self.getCache(cache_key, searchUrl)

        if data:
            soup = BeautifulSoup(data)

            resultsTable = soup.find('table', attrs={'id': 'bgtorrlist2'
                    })
            entries = resultsTable.findAll('tr')
            for result in entries[2:len(entries) - 1]:
                try:

                    info_url = result.find(href=re.compile('torrent-details'
                            ))
                    download = result.find(href=re.compile('\.torrent'))

                    if info_url and download:
                        new = {
                            'type': 'torrent',
                            'check_nzb': False,
                            'description': '',
                            'provider': self.getName(),
                            }
                        log.info('Name: %s', result.findAll('td')[1].string)
                        log.info('Seeds: %s', result.findAll('td'
                                 )[4].string)
                        log.info('Leaches: %s', result.findAll('td'
                                 )[5].string)
                        log.info('Size: %s', result.findAll('td')[7].string)

                        url = parse_qs(info_url['href'])

                        new['name'] = info_url.string
                        new['id'] = url['id'][0]
                        new['url'] = self.urls['download'] % download['href'
                                ]
                        new['size'] = self.parseSize(result.findAll('td'
                                )[7].string)
                        new['seeders'] = int(result.findAll('td')[4].string)
                        new['leechers'] = int(result.findAll('td'
                                )[5].string)
                        new['imdbid'] = movie['library']['identifier']

                        new['extra_score'] = self.extra_score
                        new['score'] = fireEvent('score.calculate', new,
                                movie, single=True)
                        is_correct_movie = fireEvent(
                            'searcher.correct_movie',
                            nzb=new,
                            movie=movie,
                            quality=quality,
                            imdb_results=True,
                            single_category=False,
                            single=True,
                            )

                        if is_correct_movie:
                            new['download'] = self.download
                            results.append(new)
                            self.found(new)
                except Exception, e:
                    log.debug(e)
                    log.info("Eroro occured during parsing! Passing only processed entries")
                    return results

            return results


    def extra_score(self, req):
        url = self.urls['detail'] % req['id']
        log.info('extra_score: %s', url)
        imdbId = req['imdbid']
        return self.imdbMatch(url, imdbId)

    def imdbMatch(self, url, imdbId):
        log.info('imdbMatch: %s', url)
        try:
            data = self.getCache(url, url)
            pass
        except IOError:
            log.error('Failed to open %s.' % url)
            return ''

        imdbIdAlt = re.sub('tt[0]*', 'tt', imdbId)
        data = unicode(data, errors='ignore')
        if 'imdb.com/title/' + imdbId in data or 'imdb.com/title/' \
            + imdbIdAlt in data:
            return 500
        return 0

    def download(self, url='', nzb_id=''):
        log.info('Downloading: %s', url)
        torrent = self.urlopen(url)
        return torrent
