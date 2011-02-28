"""
parser.http.companyParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a company.
E.g., for "Columbia Pictures [us]" the referred page would be:
    main details:   http://akas.imdb.com/company/co0071509/

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

import re
from utils import build_movie, Attribute, Extractor, DOMParserBase, \
                    analyze_imdbid

from imdb.utils import analyze_company_name


class DOMCompanyParser(DOMParserBase):
    """Parser for the main page of a given company.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        cparser = DOMCompanyParser()
        result = cparser.parse(company_html_string)
    """
    _containsObjects = True

    extractors = [
            Extractor(label='name',
                        path="//title",
                        attrs=Attribute(key='name',
                            path="./text()",
                        postprocess=lambda x: \
                                analyze_company_name(x, stripNotes=True))),

            Extractor(label='filmography',
                        group="//b/a[@name]",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../following-sibling::ol[1]/li",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./a[1]/@href",
                                'title': "./a[1]/text()",
                                'year': "./text()[1]"
                                },
                            postprocess=lambda x:
                                build_movie(u'%s %s' % \
                                (x.get('title'), x.get('year').strip()),
                                movieID=analyze_imdbid(x.get('link') or u''),
                                _parsingCompany=True))),
            ]

    preprocessors = [
        (re.compile('(<b><a name=)', re.I), r'</p>\1')
        ]

    def postprocess_data(self, data):
        for key in data.keys():
            new_key = key.replace('company', 'companies')
            new_key = new_key.replace('other', 'miscellaneous')
            new_key = new_key.replace('distributor', 'distributors')
            if new_key != key:
                data[new_key] = data[key]
                del data[key]
        return data


_OBJECTS = {
    'company_main_parser': ((DOMCompanyParser,), None)
}

