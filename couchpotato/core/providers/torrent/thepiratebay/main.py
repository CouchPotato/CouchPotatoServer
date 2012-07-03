#!/usr/bin/python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider

import re


class ThePirateBay(TorrentProvider):

    log = CPLog(__name__)
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
        self.urls = {'test': self.getapiurl(),
                     'detail': '%s/torrent/%s',
                     'search': '%s/search/%s/0/7/%d'}

    def getapiurl(self, url=''):
        return ('http://thepiratebay.se', self.conf('domain_for_tpb'
                ))[self.conf('domain_for_tpb') != None] + url

    def search(self, movie, quality):

        results = []
        if self.isDisabled():
            return results

        cache_key = 'thepiratebay.%s.%s' % (movie['library'
                ]['identifier'], quality.get('identifier'))
        search_url = self.urls['search'] % (self.getapiurl(),
                self.for_search(getTitle(movie['library']) + ' '
                + quality['identifier']),
                self.getCatId(quality['identifier'])[0])
        self.log.info('searchUrl: %s', search_url)
        data = self.getCache(cache_key, search_url)

        # print data

        if not data:
            self.log.error('Failed to get data from %s.', search_url)
            return results

        try:
            soup = BeautifulSoup(data)
            results_table = soup.find('table',
                    attrs={'id': 'searchResult'})
            entries = results_table.find_all('tr')
            for result in entries[1:]:
                link = result.find(href=re.compile('torrent\/\d+\/'))
                download = result.find(href=re.compile('magnet:'))

                # Uploaded 06-28 02:27, Size 1.37 GiB,

                size = re.search('Size (?P<size>.+),',
                                 unicode(result.select('font.detDesc'
                                 )[0])).group('size')
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
                    confirmed = (0, 30)[result.find('img',
                            alt=re.compile('Helpers')) != None]
                    moderated = (0, 50)[result.find('img',
                            alt=re.compile('Moderator')) != None]
                    is_imdb = self.imdb_match(self.getapiurl(link['href'
                            ]), movie['library']['identifier'])

                    self.log.info('Name: %s', link.string)
                    self.log.info('Seeders: %s', result.find_all('td'
                                  )[2].string)
                    self.log.info('Leechers: %s', result.find_all('td'
                                  )[3].string)
                    self.log.info('Size: %s', size)
                    self.log.info('Score(trusted + vip + moderated): %d'
                                  , confirmed + trusted + vip
                                  + moderated)

                    new['name'] = link.string
                    new['id'] = re.search('/(?P<id>\d+)/', link['href'
                            ]).group('id')
                    new['url'] = self.getapiurl(link['href'])
                    new['magnet'] = download['href']
                    new['size'] = self.parseSize(size)
                    new['seeders'] = int(result.find_all('td'
                            )[2].string)
                    new['leechers'] = int(result.find_all('td'
                            )[3].string)
                    new['extra_score'] = lambda x: confirmed + trusted \
                        + vip + moderated
                    new['score'] = fireEvent('score.calculate', new,
                            movie, single=True)

                    is_correct_movie = fireEvent(
                        'searcher.correct_movie',
                        nzb=new,
                        movie=movie,
                        quality=quality,
                        imdb_results=is_imdb,
                        single_category=False,
                        single=True,
                        )

                    if is_correct_movie:
                        results.append(new)
                        self.found(new)

            return results
        except Exception, error:
            self.log.debug(error)
            return results

    def download(self, url='', nzb_id=''):
        return url
