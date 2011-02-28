"""
parser.http.characterParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a character.
E.g., for "Jesse James" the referred pages would be:
    main details:   http://www.imdb.com/character/ch0000001/
    biography:      http://www.imdb.com/character/ch0000001/bio
    ...and so on...

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

import re
from utils import Attribute, Extractor, DOMParserBase, build_movie, \
                    analyze_imdbid
from personParser import DOMHTMLMaindetailsParser

from imdb.Movie import Movie

_personIDs = re.compile(r'/name/nm([0-9]{7})')
class DOMHTMLCharacterMaindetailsParser(DOMHTMLMaindetailsParser):
    """Parser for the "filmography" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bparser = DOMHTMLCharacterMaindetailsParser()
        result = bparser.parse(character_biography_html_string)
    """
    _containsObjects = True

    _film_attrs = [Attribute(key=None,
                      multi=True,
                      path={
                          'link': "./a[1]/@href",
                          'title': ".//text()",
                          'status': "./i/a//text()",
                          'roleID': "./a/@href"
                          },
                      postprocess=lambda x:
                          build_movie(x.get('title') or u'',
                              movieID=analyze_imdbid(x.get('link') or u''),
                              roleID=_personIDs.findall(x.get('roleID') or u''),
                              status=x.get('status') or None,
                              _parsingCharacter=True))]

    extractors = [
            Extractor(label='title',
                        path="//title",
                        attrs=Attribute(key='name',
                            path="./text()",
                            postprocess=lambda x: \
                                    x.replace(' (Character)', '').replace(
                                        '- Filmography by type', '').strip())),

            Extractor(label='headshot',
                        path="//a[@name='headshot']",
                        attrs=Attribute(key='headshot',
                            path="./img/@src")),

            Extractor(label='akas',
                        path="//div[h5='Alternate Names:']",
                        attrs=Attribute(key='akas',
                            path="./div//text()",
                            postprocess=lambda x: x.strip().split(' / '))),

            Extractor(label='filmography',
                        path="//div[@class='filmo'][not(h5)]/ol/li",
                        attrs=_film_attrs),

            Extractor(label='filmography sections',
                        group="//div[@class='filmo'][h5]",
                        group_key="./h5/a/text()",
                        group_key_normalize=lambda x: x.lower()[:-1],
                        path="./ol/li",
                        attrs=_film_attrs),
            ]

    preprocessors = [
            # Check that this doesn't cut "status"...
            (re.compile(r'<br>(\.\.\.|   ).+?</li>', re.I | re.M), '</li>')]


class DOMHTMLCharacterBioParser(DOMParserBase):
    """Parser for the "biography" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bparser = DOMHTMLCharacterBioParser()
        result = bparser.parse(character_biography_html_string)
    """
    _defGetRefs = True

    extractors = [
            Extractor(label='introduction',
                        path="//div[@id='_intro']",
                        attrs=Attribute(key='introduction',
                            path=".//text()",
                            postprocess=lambda x: x.strip())),

            Extractor(label='biography',
                        path="//span[@class='_biography']",
                        attrs=Attribute(key='biography',
                            multi=True,
                            path={
                                'info': "./preceding-sibling::h4[1]//text()",
                                'text': ".//text()"
                            },
                            postprocess=lambda x: u'%s: %s' % (
                                x.get('info').strip(),
                                x.get('text').replace('\n',
                                    ' ').replace('||', '\n\n').strip()))),
    ]

    preprocessors = [
        (re.compile('(<div id="swiki.2.3.1">)', re.I), r'\1<div id="_intro">'),
        (re.compile('(<a name="history">)\s*(<table .*?</table>)',
                    re.I | re.DOTALL),
         r'</div>\2\1</a>'),
        (re.compile('(<a name="[^"]+">)(<h4>)', re.I), r'</span>\1</a>\2'),
        (re.compile('(</h4>)</a>', re.I), r'\1<span class="_biography">'),
        (re.compile('<br/><br/>', re.I), r'||'),
        (re.compile('\|\|\n', re.I), r'</span>'),
        ]


class DOMHTMLCharacterQuotesParser(DOMParserBase):
    """Parser for the "quotes" page of a given character.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        qparser = DOMHTMLCharacterQuotesParser()
        result = qparser.parse(character_quotes_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='charquotes',
                    group="//h5",
                    group_key="./a/text()",
                    path="./following-sibling::div[1]",
                    attrs=Attribute(key=None,
                        path={'txt': ".//text()",
                              'movieID': ".//a[1]/@href"},
                        postprocess=lambda x: (analyze_imdbid(x['movieID']),
                                    x['txt'].strip().replace(':   ',
                                    ': ').replace(':  ', ': ').split('||'))))
    ]

    preprocessors = [
        (re.compile('(</h5>)', re.I), r'\1<div>'),
        (re.compile('\s*<br/><br/>\s*', re.I), r'||'),
        (re.compile('\|\|\s*(<hr/>)', re.I), r'</div>\1'),
        (re.compile('\s*<br/>\s*', re.I), r'::')
        ]

    def postprocess_data(self, data):
        if not data:
            return {}
        newData = {}
        for title in data:
            movieID, quotes = data[title]
            if movieID is None:
                movie = title
            else:
                movie = Movie(title=title, movieID=movieID,
                              accessSystem=self._as, modFunct=self._modFunct)
            newData[movie] = [quote.split('::') for quote in quotes]
        return {'quotes': newData}


from personParser import DOMHTMLSeriesParser

_OBJECTS = {
    'character_main_parser': ((DOMHTMLCharacterMaindetailsParser,),
                                {'kind': 'character'}),
    'character_series_parser': ((DOMHTMLSeriesParser,), None),
    'character_bio_parser': ((DOMHTMLCharacterBioParser,), None),
    'character_quotes_parser': ((DOMHTMLCharacterQuotesParser,), None)
}


