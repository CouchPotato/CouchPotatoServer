"""
parser.http.searchPersonParser module (imdb package).

This module provides the HTMLSearchPersonParser class (and the
search_person_parser instance), used to parse the results of a search
for a given person.
E.g., when searching for the name "Mel Gibson", the parsed page would be:
    http://akas.imdb.com/find?q=Mel+Gibson&nm=on&mx=20

Copyright 2004-2010 Davide Alberani <da@erlug.linux.it>
               2008 H. Turgut Uyar <uyar@tekir.org>

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

import re
from imdb.utils import analyze_name, build_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser


def _cleanName(n):
    """Clean the name in a title tag."""
    if not n:
        return u''
    n = n.replace('Filmography by type for', '') # FIXME: temporary.
    return n

class DOMBasicPersonParser(DOMBasicMovieParser):
    """Simply get the name of a person and the imdbID.

    It's used by the DOMHTMLSearchPersonParser class to return a result
    for a direct match (when a search on IMDb results in a single
    person, the web server sends directly the movie page."""
    _titleFunct = lambda self, x: analyze_name(_cleanName(x), canonical=1)


_reAKASp = re.compile(r'(?:aka|birth name) (<em>")(.*?)"(<br>|<\/em>|<\/td>)',
                    re.I | re.M)

class DOMHTMLSearchPersonParser(DOMHTMLSearchMovieParser):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, for persons."""
    _BaseParser = DOMBasicPersonParser
    _notDirectHitTitle = '<title>imdb name'
    _titleBuilder = lambda self, x: build_name(x, canonical=True)
    _linkPrefix = '/name/nm'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()",
                            'index': "./text()[1]",
                            'akas': ".//div[@class='_imdbpyAKA']/text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            analyze_name((x.get('name') or u'') + \
                                        (x.get('index') or u''),
                                         canonical=1), x.get('akas')
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, '/name/nm')]/..",
                            attrs=_attrs)]

    def preprocess_string(self, html_string):
        if self._notDirectHitTitle in html_string[:1024].lower():
            html_string = _reAKASp.sub(
                                    r'\1<div class="_imdbpyAKA">\2::</div>\3',
                                    html_string)
        return DOMHTMLSearchMovieParser.preprocess_string(self, html_string)


_OBJECTS = {
        'search_person_parser': ((DOMHTMLSearchPersonParser,),
                    {'kind': 'person', '_basic_parser': DOMBasicPersonParser})
}

