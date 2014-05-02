# -*- coding: utf-8 -*-
import json
import re
import urllib

from core.helpers.variable import getIdentifier
from core.media._base.providers.och.base import OCHProvider
from couchpotato.core.logger import CPLog
from bs4 import BeautifulSoup

log = CPLog(__name__)


class Base(OCHProvider):
    urls = {
        'search': 'http://hd-city.org/?s=%s',
    }

    def _search(self, media, quality, results):
        identifier = re.match(r"tt(\d{7})", getIdentifier(media)).group(1)
        searchUrl = self.urls['search'] % (urllib.quote_plus(identifier))

        log.debug('fetching data from %s' % searchUrl)

        data = self.getHTMLData(searchUrl)

        for res in self.parseSearchResult(data):
            res['imdb'] = getIdentifier(media)
            results.append(res)


    #===============================================================================
    # INTERNAL METHODS
    #===============================================================================

    def parseSearchResult(self, data):
        results = []

        dom = BeautifulSoup(data)

        content = dom.div.find(id='content').find(attrs={"class": "main"})
        titleTags = content.findAll(attrs={"class": "single-top"}, recursive=False)
        infoTags = content.findAll(attrs={"class": "single"}, recursive=False)

        log.info('Found %s %s on search.', (len(titleTags), 'release' if len(titleTags) == 1 else 'releases'))

        for titleTag, infoTag in zip(titleTags, infoTags):

            #linksToMovieDetails.append(titleTag.a['href'])
            title = titleTag.a.text

            try:
                dateTag = titleTag.find(attrs={"class": "single-info"}).text
                date = re.search(r'\d{1,2}\.\s\w+\s\d{4}', dateTag).group(0)
            except AttributeError:
                date = None
                log.debug("Error parsing releasedate of %s." % title)

            urlList = []
            size = -1
            try:
                for strongTag in infoTag.findAll('p')[-1].findAll('strong'):
                    if not 'download' in strongTag.text.lower() and not 'mirror' in strongTag.text.lower() : continue

                    link = strongTag.findNextSibling()['href']
                    hoster = strongTag.findNextSibling().text

                    for acceptedHoster in self.conf('hosters').replace(' ', '').split(','):
                        if acceptedHoster in hoster.lower() and link not in urlList:
                            urlList.append(link)
                            log.debug('Found new DL-Link %s on Hoster %s' % (urlList, hoster))
                if urlList != []:
                    urlList = json.dumps(urlList)    #List 2 string for db-compatibility
                else:
                    continue

                sizeTag = infoTag.find('b', text=re.compile(u"Größe:", re.UNICODE))
                if sizeTag is None:
                    sizeTag = infoTag.find('strong', text=re.compile(u"Größe:", re.UNICODE))
                size = self.parseSize(sizeTag.nextSibling.strip().replace(',', '.'))
            except:
                log.error('Error parsing movielinks of release %s.' % title)

            results.append({
                'name': title,
                'id': hash(title),
                'date': date,
                'url': urlList,
                'size': size
            })

        return results


config = [{
              'name': 'hdcity',
              'groups': [
                  {
                      'tab': 'searcher',
                      'list': 'och_providers',
                      'name': 'HD-City',
                      'description': 'See <a href="https://www.hd-city.org">HD-City.org</a>.',
                      'wizard': True,
                      'options': [
                          {
                              'name': 'enabled',
                              'type': 'enabler',
                          },
                          {
                              'name': 'extra_score',
                              'advanced': True,
                              'label': 'Extra Score',
                              'type': 'int',
                              'default': 0,
                              'description': 'Starting score for each release found via this provider.',
                          },
                          {
                              'name': 'hosters',
                              'label': 'accepted Hosters',
                              'default': '',
                              'placeholder': 'Example: uploaded,share-online',
                              'description': 'List of Hosters separated by ",". Should be at least one!'
                          },
                      ],
                  },
              ],
          }]
