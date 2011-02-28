"""
parser.http.topBottomParser module (imdb package).

This module provides the classes (and the instances), used to parse the
lists of top 250 and bottom 100 movies.
E.g.:
    http://akas.imdb.com/chart/top
    http://akas.imdb.com/chart/bottom

Copyright 2009 Davide Alberani <da@erlug.linux.it>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from imdb.utils import analyze_title
from utils import DOMParserBase, Attribute, Extractor, analyze_imdbid


class DOMHTMLTop250Parser(DOMParserBase):
    """Parser for the "top 250" page.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLTop250Parser()
        result = tparser.parse(top250_html_string)
    """
    label = 'top 250'
    ranktext = 'top 250 rank'

    def _init(self):
        self.extractors = [Extractor(label=self.label,
                        path="//div[@id='main']//table//tr",
                        attrs=Attribute(key=None,
                                multi=True,
                                path={self.ranktext: "./td[1]//text()",
                                        'rating': "./td[2]//text()",
                                        'title': "./td[3]//text()",
                                        'movieID': "./td[3]//a/@href",
                                        'votes': "./td[4]//text()"
                                        }))]

    def postprocess_data(self, data):
        if not data or self.label not in data:
            return []
        mlist = []
        data = data[self.label]
        # Avoid duplicates.  A real fix, using XPath, is auspicabile.
        # XXX: probably this is no more needed.
        seenIDs = []
        for d in data:
            if 'movieID' not in d: continue
            if self.ranktext not in d: continue
            if 'title' not in d: continue
            theID = analyze_imdbid(d['movieID'])
            if theID is None:
                continue
            theID = str(theID)
            if theID in seenIDs:
                continue
            seenIDs.append(theID)
            minfo = analyze_title(d['title'])
            try: minfo[self.ranktext] = int(d[self.ranktext].replace('.', ''))
            except: pass
            if 'votes' in d:
                try: minfo['votes'] = int(d['votes'].replace(',', ''))
                except: pass
            if 'rating' in d:
                try: minfo['rating'] = float(d['rating'])
                except: pass
            mlist.append((theID, minfo))
        return mlist


class DOMHTMLBottom100Parser(DOMHTMLTop250Parser):
    """Parser for the "bottom 100" page.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLBottom100Parser()
        result = tparser.parse(bottom100_html_string)
    """
    label = 'bottom 100'
    ranktext = 'bottom 100 rank'


_OBJECTS = {
    'top250_parser':  ((DOMHTMLTop250Parser,), None),
    'bottom100_parser':  ((DOMHTMLBottom100Parser,), None)
}

