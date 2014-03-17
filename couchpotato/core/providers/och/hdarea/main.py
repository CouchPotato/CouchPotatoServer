import re
import traceback
from datetime import date
import bs4
from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.och.base import OCHProvider
from couchpotato.core.helpers.variable import tryInt
from bs4 import BeautifulSoup, NavigableString

log = CPLog(__name__)


class hdarea(OCHProvider):
    urls = {
        'search': 'http://www.hd-area.org/?s=search&q=%s',
    }

    def _searchOnTitle(self, title, movie, quality, results):
        titles = movie['library']['info'].get('alt_titles', [])
        titles.append(title)
        for title in titles:
            query = '"%s"' % (simplifyString(title))
            searchUrl = self.urls['search'] % query

            log.debug('fetching data from %s' % searchUrl)
            data = self.getHTMLData(searchUrl)

            linksToMovieDetails = self.parseSearchResult(data)
            for movieDetailLink in linksToMovieDetails:
                data = self.getHTMLData(movieDetailLink)
                result = self.parseMovieDetailPage(data)
                if len(result):
                    result['id'] = movieDetailLink.split('id=')[1]
                    results.append(result)


    #===============================================================================
    # INTERNAL METHODS
    #===============================================================================
    def parseDownload(self, download):
        res = {}
        try:
            for child in download.descendants:
                if not isinstance(child, NavigableString) and "cover" in child["class"]:
                    if "beschreibung" in child.div["class"]:
                        descr = child.div
                        links = descr.findAll('span', attrs={"style": "display:inline;"}, recursive=True)
                        for link in links:
                            url = link.a["href"]
                            hoster = link.text
                            for acceptedHoster in self.conf('hosters'):
                                if acceptedHoster in hoster.lower():
                                    res["url"] = url
                                    return res
        except (TypeError, KeyError):
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
        return res

    def parseSearchResult(self, data):
        #print data
        dom = BeautifulSoup(data)

        content = dom.find(id='content')
        MovieEntries = content.find(attrs={"class": "whitecontent contentheight"}, recursive=False)

        linksToMovieDetails = []
        for link in MovieEntries.findAll('a'):
            linksToMovieDetails.append(link['href'])
        return linksToMovieDetails
