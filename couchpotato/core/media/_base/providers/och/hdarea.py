# -*- coding: utf-8 -*-

import re
import traceback
from datetime import date
import bs4
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from core.media._base.providers.och.base import OCHProvider
from couchpotato.core.helpers.variable import tryInt
from bs4 import BeautifulSoup, NavigableString
import json

log = CPLog(__name__)
rarPassword = 'hd-area.org'

class Base(OCHProvider):
    urls = {
        'search': 'http://www.hd-area.org/?s=search&q=%s',
    }

    def _searchOnTitle(self, title, movie, quality, results):
        #Nach Lokalem Titel (abh. vom def. Laendercode) und original Titel suchen
        alt_titles = movie['library']['info'].get('alternate_titles', [])
        titles = []
        titles.extend(alt_titles); titles.append(title)
        for title in titles:
            self.do_search(title, results)
        if not results:
            shortenedAltTitles = []
             # trying to delete original title string from alt title string
            for alt_title in alt_titles:
                if alt_title != title and title in alt_title:
                    shortenedAltTitle = simplifyString(alt_title).replace(simplifyString(title), "")
                    if shortenedAltTitle != "":
                        self.do_search(shortenedAltTitle, results)


    def do_search(self, title, results):
        query = '"%s"' % (simplifyString(title))
        searchUrl = self.urls['search'] % query

        log.debug('fetching data from %s' % searchUrl)

        #TODO: Search result has more than one page <vorwaerts> link
        data = self.getHTMLData(searchUrl)

        linksToMovieDetails = self.parseSearchResult(data)
        for movieDetailLink in linksToMovieDetails:
            log.debug("fetching data from Movie's detail page %s" % movieDetailLink)
            data = self.getHTMLData(movieDetailLink)
            result = self.parseMovieDetailPage(data)
            if len(result):
                result['id'] = movieDetailLink.split('id=')[1]
                results.append(result)
        return len(linksToMovieDetails)


    #===============================================================================
    # INTERNAL METHODS
    #===============================================================================
    def parseDownload(self, download):
        res = {}
        try:
            #child-Abschnitte des Page-Src. nach div.beschreibung durchsuchen
            descr = download.find(attrs={"class": "beschreibung"})
            #Suche nach Jahr und der Release-Groesse des Film-Releases
            log.debug("Look for release info and dl-links on Movie's detail page.")
            try:
                matches = descr.findAll('strong', attrs={"class": "main"}, recursive=True)
                for match in matches:
                    if "Jahr:" in match:
                        try:
                            year = re.search(r"[0-9]{4}", str(match.nextSibling)).group()
                            res["year"] = year
                            log.debug('Found release year of movie: %s' % year)
                        except (AttributeError, TypeError):
                            log.debug('Release year of movie not found!')
                    if u"Größe:" in match:
                        try:
                            size_raw = re.search(r"[0-9]+([,.][0-9]+)?\s+\w+", str(match.nextSibling)).group()
                            size = self.parseSize(str(size_raw,).replace(',','.'))
                            res["size"] = size
                            log.debug('Found size of release: %s Mb' % size)
                        except (AttributeError, TypeError):
                            log.debug('Size of movie release not found!')
            except (AttributeError, TypeError, KeyError):
                log.error('Could not fetch release details from Release Website.')

            #Suche nach Links und pruefe auf invisible (teilw. veraltete Links im Code). Filtere Hoster.
            try:
                if self.conf('hosters') == '':
                    log.error('Hosterlist seems to be empty, please check settings.')
                    return None

                links = descr.findAll('span', attrs={"style": "display:inline;"}, recursive=True)
                res["url"] = []
                for link in links:
                    url = link.a["href"]
                    hoster = link.text
                    for acceptedHoster in self.conf('hosters').replace(' ', '').split(','):
                        if acceptedHoster in hoster.lower() and url not in res["url"]:
                            res["url"].append(url)
                            log.debug('Found new DL-Link %s on Hoster %s' % (url, hoster))
                            #return res
                if res["url"] != []:
                    res["url"] = json.dumps(res["url"])    #List 2 string for db-compatibility
                    return res
                else:
                    log.debug('No DL-Links on Hoster(s) [%s] found :(' % (self.conf('hosters')))
                    return None
            except (AttributeError, TypeError, KeyError):
                log.error('Could not fetch dl-Links from Release Website.')
        except (AttributeError, TypeError, KeyError):
            return None
        return None

    def parseTopBox(self, topbox):
        def _getCentury(year):
            if len(year) > 2:
                return year
            elif tryInt(year[0]) in xrange(3):
                return '20' + year
            else:
                return '19' + year

        res = {}
        for child in topbox.descendants:
            try:
                try:
                    if not isinstance(child, NavigableString) and ("title" and "topinfo") in child["class"]:
                        match = re.match(
                            r"Uploader: (?P<uploader>\w+).+Datum:\s+(?P<date>\w+\.\w+.\w+).{3}Kategorie\s(?P<category>.+)",
                            child.text)
                        #res["uploader"] = match.group('uploader')
                        relDate = match.group('date').split('.')
                        res["age"] = (date.today() - date(tryInt(_getCentury(relDate[2])), tryInt(relDate[1]),
                                                          tryInt(relDate[0]))).days
                        #res["category"] = match.group('category').split(" > ")
                except AttributeError:
                    log.error("error parsing topbox of release %s" % res['name'])
                if not isinstance(child, NavigableString) and ("boxrechts" in child["class"]):
                    res['description'] = child.a["href"].split("/")[-2] #adding imdb-id
                elif not isinstance(child, NavigableString) and "title" in child["class"]:
                    res['name'] = child.a["title"]
            except (TypeError, KeyError, IndexError):
                pass
        return res

    def parseMovieDetailPage(self, data):
        dom = BeautifulSoup(data)
        content = dom.find(id='content')

        topbox = content.findAll(attrs={"class": "topbox"}, recursive=False)
        download = content.findAll(attrs={"class": "download"}, recursive=False)
        dlbottom = content.findAll(attrs={"class": "dlbottom"}, recursive=False)

        assert len(topbox) == len(download) == len(dlbottom)

        res = {}
        if len(topbox) > 0 and len(download) > 0:
            tb = self.parseTopBox(topbox[0])
            dl = self.parseDownload(download[0])
            if tb is not None and dl is not None:
                res.update(tb)
                res.update(dl)
                res['pwd'] = rarPassword
        return res

    def parseSearchResult(self, data):
        #print data
        try:
            dom = BeautifulSoup(data)

            content = dom.find(id='content')
            MovieEntries = content.find(attrs={"class": "whitecontent contentheight"}, recursive=False)

            linksToMovieDetails = []
            for link in MovieEntries.findAll('a', recursive=False):
                linksToMovieDetails.append(link['href'])
            num_results = len(linksToMovieDetails)
            log.info('Found %s %s on search.', (num_results, 'release' if num_results == 1 else 'releases'))
            return linksToMovieDetails
        except:
            log.debug('There are no search results to parse!')
            return []


config = [{
    'name': 'hdarea',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'och_providers',
            'name': 'HD-Area',
            'description': 'See <a href="https://www.hd-area.org">HD-Area.org</a>',
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