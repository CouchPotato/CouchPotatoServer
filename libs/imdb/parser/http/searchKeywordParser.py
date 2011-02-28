"""
parser.http.searchKeywordParser module (imdb package).

This module provides the HTMLSearchKeywordParser class (and the
search_company_parser instance), used to parse the results of a search
for a given keyword.
E.g., when searching for the keyword "alabama", the parsed page would be:
    http://akas.imdb.com/find?s=kw;mx=20;q=alabama

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

from utils import Extractor, Attribute, analyze_imdbid
from imdb.utils import analyze_title, analyze_company_name

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser

class DOMBasicKeywordParser(DOMBasicMovieParser):
    """Simply get the name of a keyword.

    It's used by the DOMHTMLSearchKeywordParser class to return a result
    for a direct match (when a search on IMDb results in a single
    keyword, the web server sends directly the keyword page.
    """
    # XXX: it's still to be tested!
    # I'm not even sure there can be a direct hit, searching for keywords.
    _titleFunct = lambda self, x: analyze_company_name(x or u'')


class DOMHTMLSearchKeywordParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, searching for keywords similar to
    the one given."""

    _BaseParser = DOMBasicKeywordParser
    _notDirectHitTitle = '<title>imdb keyword'
    _titleBuilder = lambda self, x: x
    _linkPrefix = '/keyword/'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path="./a[1]/text()"
                            )]
    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/keyword/')]/..",
                            attrs=_attrs)]


def custom_analyze_title4kwd(title, yearNote, outline):
    """Return a dictionary with the needed info."""
    title = title.strip()
    if not title:
        return {}
    if yearNote:
        yearNote = '%s)' % yearNote.split(' ')[0]
        title = title + ' ' + yearNote
    retDict = analyze_title(title)
    if outline:
        retDict['plot outline'] = outline
    return retDict


class DOMHTMLSearchMovieKeywordParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, searching for movies with the given
    keyword."""

    _notDirectHitTitle = '<title>best'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'info': "./a[1]//text()",
                            'ynote': "./span[@class='desc']/text()",
                            'outline': "./span[@class='outline']//text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            custom_analyze_title4kwd(x.get('info') or u'',
                                                    x.get('ynote') or u'',
                                                    x.get('outline') or u'')
                        ))]

    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/title/tt')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_keyword_parser': ((DOMHTMLSearchKeywordParser,),
                {'kind': 'keyword', '_basic_parser': DOMBasicKeywordParser}),
        'search_moviekeyword_parser': ((DOMHTMLSearchMovieKeywordParser,), None)
}

