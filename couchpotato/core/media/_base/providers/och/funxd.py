# -*- coding: utf-8 -*-
import json
import re
from datetime import date
import urllib
import time
import datetime

from couchpotato.core.helpers.encoding import simplifyString
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.och.base import OCHProvider
from bs4 import BeautifulSoup

log = CPLog(__name__)


class Base(OCHProvider):
    urls = {
        'search': 'http://funxd.in/?s=%s',
    }

    def _searchOnTitle(self, title, movie, quality, results):
        #Nach Lokalem Titel (abh. vom def. Laendercode) und original Titel suchen
        alt_titles = movie['info'].get('alternate_titles', [])
        titles = []
        titles.extend(alt_titles);
        titles.append(title)
        for title in titles:
            self.do_search(simplifyString(title), results)
        if not results:
            shortenedAltTitles = []
            # trying to delete original title string from alt title string
            for alt_title in alt_titles:
                if alt_title != title and title in alt_title:
                    shortenedAltTitle = simplifyString(alt_title).replace(simplifyString(title), "")
                    if shortenedAltTitle != "":
                        self.do_search(shortenedAltTitle, results)


    def do_search(self, title, results):
        query = '%s' % (urllib.quote_plus(title))
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
                results.append(result)
        return len(linksToMovieDetails)


    #===============================================================================
    # INTERNAL METHODS
    #===============================================================================

    def parseComments(self, comments):
        for c in comments:
            try:
                imdbMatch = re.search(r"imdb.com/title/(?P<imdb_id>tt[0-9]{7})", str(c))
                if bool(imdbMatch):
                    imdb = imdbMatch.group("imdb_id")
                    return {'description': imdb}
            except AttributeError, e:
                log.error('Something went wrong when trying to parse imdb-id from comment %s.' % str(c))

    def parsePost(self, post):
        def _getDateObject(day, month, year):
            months = ["january", "february", "march", "april", "may", "june", "juli", "august", "september", "october", "november", "december"]
            try:
                month = months.index(month.lower()) + 1
                return datetime.date(tryInt(year), month, tryInt(day))
            except:
                raise

        id = post.attrs["id"].split("-")[1]

        title = post.h2.a.attrs["title"]

        relDate = None
        try:
            relDateString = post.find(attrs={"class": "simple_date"}).text.split("on")[1].strip()
            year = relDateString.split(",")[1].strip()
            month = relDateString.split(" ")[0].strip()
            day = relDateString.split(" ")[1].strip()[:-1]
            relDate = _getDateObject(day, month, year)
        except:
            log.error(
                "error while parsing date. %s" % relDateString)

        size_raw = str(post.find('strong', text='Size:').nextSibling).strip()
        size = self.parseSize(size_raw.replace(',', '.'))

        #release = str(post.find('strong', text='Release:').nextSibling).strip()

        url = ""
        for p in post.findAll("p"):
            if re.search(r"(share-online|uploaded)", str(p.a), re.IGNORECASE):
                url = p.a.attrs['href']
                break

        return {"id": id,
                "name": title,
                "age": (date.today() - relDate).days if relDate is not None else 0,
                "size": size,
                "url": json.dumps([url])}

    def parseMovieDetailPage(self, data):
        dom = BeautifulSoup(data)
        content = dom.find(id='content-body')

        post = content.find(attrs={"class": "post"}, recursive=False)
        comments = content.findAll(attrs={"class": "comment_content"}, recursive=True)

        commentContent = self.parseComments(comments)
        postContent = self.parsePost(post)

        res = {}
        if commentContent is not None and postContent is not None:
            res.update(commentContent)
            res.update(postContent)
            res["pwd"] = "funxd"  # hardcoded, is static on funxd page
        return res

    def parseSearchResult(self, data):
        #print data
        try:
            dom = BeautifulSoup(data)

            content = dom.find(id='content-body')

            linksToMovieDetails = []
            for link in content.findAll('a', recursive=False):
                linksToMovieDetails.append(link['href'])
            num_results = len(linksToMovieDetails)
            log.info('Found %s %s on search.', (num_results, 'release' if num_results == 1 else 'releases'))
            return linksToMovieDetails
        except:
            log.debug('There are no search results to parse!')
            return []


config = [{
              'name': 'funxd',
              'groups': [
                  {
                      'tab': 'searcher',
                      'list': 'och_providers',
                      'name': 'FunXD.in',
                      'description': 'See <a href="https://www.funxd.in">funXD.in</a>',
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
