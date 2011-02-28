"""
parser.http.searchCharacterParser module (imdb package).

This module provides the HTMLSearchCharacterParser class (and the
search_character_parser instance), used to parse the results of a search
for a given character.
E.g., when searching for the name "Jesse James", the parsed page would be:
    http://akas.imdb.com/find?s=Characters;mx=20;q=Jesse+James

Copyright 2007-2009 Davide Alberani <da@erlug.linux.it>
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

from imdb.utils import analyze_name, build_name
from utils import Extractor, Attribute, analyze_imdbid

from searchMovieParser import DOMHTMLSearchMovieParser, DOMBasicMovieParser


class DOMBasicCharacterParser(DOMBasicMovieParser):
    """Simply get the name of a character and the imdbID.

    It's used by the DOMHTMLSearchCharacterParser class to return a result
    for a direct match (when a search on IMDb results in a single
    character, the web server sends directly the movie page."""
    _titleFunct = lambda self, x: analyze_name(x or u'', canonical=False)


class DOMHTMLSearchCharacterParser(DOMHTMLSearchMovieParser):
    _BaseParser = DOMBasicCharacterParser
    _notDirectHitTitle = '<title>imdb search'
    _titleBuilder = lambda self, x: build_name(x, canonical=False)
    _linkPrefix = '/character/ch'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'name': "./a[1]/text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            {'name': x.get('name')}
                        ))]
    extractors = [Extractor(label='search',
                            path="//td[3]/a[starts-with(@href, " \
                                    "'/character/ch')]/..",
                            attrs=_attrs)]


_OBJECTS = {
        'search_character_parser': ((DOMHTMLSearchCharacterParser,),
                {'kind': 'character', '_basic_parser': DOMBasicCharacterParser})
}

