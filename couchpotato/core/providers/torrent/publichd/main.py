#!/usr/bin/python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from couchpotato.core.event import fireEvent
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentProvider
from urlparse import parse_qs

import re


class PublicHD(TorrentProvider):

    log = CPLog(__name__)
    urls = {
        'test': 'http://publichd.eu',
        'download': 'http://publichd.eu/%s',
        'detail': 'http://publichd.eu/index.php?page=torrent-details&id=%s',
        'search': 'http://publichd.eu/index.php?page=torrents&search=%s&active=1&category=%d',
        }

    cat_ids = [([2], ['720p']), ([5], ['1080p']), ([16], ['brrip']),
               ([16], ['bd50'])]

    cat_backup_id = 0

    def search(self, movie, quality):

        results = []
        if self.isDisabled() and quality['hd'] != True:
            return results

        cache_key = 'publichd.%s.%s' % (movie['library']['identifier'],
                quality.get('identifier'))
        search_url = self.urls['search'] \
            % (self.for_search(getTitle(movie['library'])
               + ' ' + quality['identifier']),
               self.getCatId(quality['identifier'])[0])
        self.log.info('searchUrl: %s', search_url)
        data = self.getCache(cache_key, search_url)
        if not data:
            self.log.error('Failed to get data from %s.', search_url)
            return results

        try:
            soup = BeautifulSoup(data)

            results_table = soup.find('table',
                    attrs={'id': 'bgtorrlist2'})
            entries = results_table.find_all('tr')
            for result in entries[2:len(entries) - 1]:
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
                    self.log.debug('Name: %s', result.find_all('td'
                                   )[1].string)
                    self.log.debug('Seeders: %s', result.find_all('td'
                                   )[4].string)
                    self.log.debug('Leaches: %s', result.find_all('td'
                                   )[5].string)
                    self.log.debug('Size: %s', result.find_all('td'
                                   )[7].string)

                    url = parse_qs(info_url['href'])

                    new['name'] = info_url.string
                    new['id'] = url['id'][0]
                    new['url'] = self.urls['download'] % download['href'
                            ]
                    new['size'] = self.parseSize(result.find_all('td'
                            )[7].string)
                    new['seeders'] = int(result.find_all('td'
                            )[4].string)
                    new['leechers'] = int(result.find_all('td'
                            )[5].string)

                    new['score'] = fireEvent('score.calculate', new,
                            movie, single=True)
                    is_imdb = self.imdb_match(self.urls['detail']
                            % new['id'], movie['library']['identifier'])
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
                        new['download'] = self.download
                        results.append(new)
                        self.found(new)

            return results
        except Exception, err:
            self.log.debug(err)
            self.log.info('Error occured during parsing! Passing only processed entries'
                          )
            return results

    def download(self, url='', nzb_id=''):
        self.log.info('Downloading: %s', url)
        torrent = self.urlopen(url)
        return torrent
