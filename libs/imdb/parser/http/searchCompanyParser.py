"""
parser.http.searchCompanyParser module (imdb package).

This module provides the HTMLSearchCompanyParser class (and the
search_company_parser instance), used to parse the results of a search
for a given company.
E.g., when searching for the name "Columbia Pictures", the parsed page would be:
    http://akas.imdb.com/find?s=co;mx=20;q=Columbia+Pictures

Copyright 2008-2009 Davide Alberani <da@erlug.linux.it>
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

from imdb.utils import analyze_company_name, build_company_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser

class DOMBasicCompanyParser(DOMBasicMovieParser):
    """Simply get the name of a company and the imdbID.

    It's used by the DOMHTMLSearchCompanyParser class to return a result
    for a direct match (when a search on IMDb results in a single
    company, the web server sends directly the company page.
    """
    _titleFunct = lambda self, x: analyze_company_name(x or u'')


class DOMHTMLSearchCompanyParser(DOMHTMLSearchMovieParser):
    _BaseParser = DOMBasicCompanyParser
    _notDirectHitTitle = '<title>imdb company'
    _titleBuilder = lambda self, x: build_company_name(x)
    _linkPrefix = '/company/co'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()",
                            'notes': "./text()[1]"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link')),
                            analyze_company_name(x.get('name')+(x.get('notes')
                                                or u''), stripNotes=True)
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/company/co')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_company_parser': ((DOMHTMLSearchCompanyParser,),
                {'kind': 'company', '_basic_parser': DOMBasicCompanyParser})
}

