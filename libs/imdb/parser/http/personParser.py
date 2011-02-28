"""
parser.http.personParser module (imdb package).

This module provides the classes (and the instances), used to parse
the IMDb pages on the akas.imdb.com server about a person.
E.g., for "Mel Gibson" the referred pages would be:
    categorized:    http://akas.imdb.com/name/nm0000154/maindetails
    biography:      http://akas.imdb.com/name/nm0000154/bio
    ...and so on...

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
from imdb.Movie import Movie
from imdb.utils import analyze_name, canonicalName, normalizeName, \
                        analyze_title, date_and_notes
from utils import build_movie, DOMParserBase, Attribute, Extractor, \
                        analyze_imdbid


from movieParser import _manageRoles
_reRoles = re.compile(r'(<li>.*? \.\.\.\. )(.*?)(</li>|<br>)',
                        re.I | re.M | re.S)

def build_date(date):
    day = date.get('day')
    year = date.get('year')
    if day and year:
        return "%s %s" % (day, year)
    if day:
        return day
    if year:
        return year
    return ""

class DOMHTMLMaindetailsParser(DOMParserBase):
    """Parser for the "categorized" (maindetails) page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        cparser = DOMHTMLMaindetailsParser()
        result = cparser.parse(categorized_html_string)
    """
    _containsObjects = True

    _birth_attrs = [Attribute(key='birth date',
                        path={
                            'day': "./div/a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./div/a[starts-with(@href, " \
                                    "'/search/name?birth_year=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='birth notes',
                        path="./div/a[starts-with(@href, " \
                                "'/search/name?birth_place=')]/text()")]
    _death_attrs = [Attribute(key='death date',
                        path={
                            'day': "./div/a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./div/a[starts-with(@href, " \
                                    "'/search/name?death_date=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='death notes',
                        path="./div/text()",
                        # TODO: check if this slicing is always correct
                        postprocess=lambda x: x.strip()[2:])]
    _film_attrs = [Attribute(key=None,
                      multi=True,
                      path={
                          'link': "./a[1]/@href",
                          'title': ".//text()",
                          'status': "./i/a//text()",
                          'roleID': "./div[@class='_imdbpyrole']/@roleid"
                          },
                      postprocess=lambda x:
                          build_movie(x.get('title') or u'',
                              movieID=analyze_imdbid(x.get('link') or u''),
                              roleID=(x.get('roleID') or u'').split('/'),
                              status=x.get('status') or None))]

    extractors = [
            Extractor(label='page title',
                        path="//title",
                        attrs=Attribute(key='name',
                            path="./text()",
                            postprocess=lambda x: analyze_name(x,
                                                            canonical=1))),

            Extractor(label='birth info',
                        path="//div[h5='Date of Birth:']",
                        attrs=_birth_attrs),

            Extractor(label='death info',
                        path="//div[h5='Date of Death:']",
                        attrs=_death_attrs),

            Extractor(label='headshot',
                        path="//a[@name='headshot']",
                        attrs=Attribute(key='headshot',
                            path="./img/@src")),

            Extractor(label='akas',
                        path="//div[h5='Alternate Names:']",
                        attrs=Attribute(key='akas',
                            path="./div/text()",
                            postprocess=lambda x: x.strip().split(' | '))),

            Extractor(label='filmography',
                        group="//div[@class='filmo'][h5]",
                        group_key="./h5/a[@name]/text()",
                        group_key_normalize=lambda x: x.lower()[:-1],
                        path="./ol/li",
                        attrs=_film_attrs)
            ]
    preprocessors = [
            # XXX: check that this doesn't cut "status" or other info...
            (re.compile(r'<br>(\.\.\.|    ?).+?</li>', re.I | re.M | re.S),
                '</li>'),
            (_reRoles, _manageRoles)]

    def postprocess_data(self, data):
        for what in 'birth date', 'death date':
            if what in data and not data[what]:
                del data[what]
        return data


class DOMHTMLBioParser(DOMParserBase):
    """Parser for the "biography" page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        bioparser = DOMHTMLBioParser()
        result = bioparser.parse(biography_html_string)
    """
    _defGetRefs = True

    _birth_attrs = [Attribute(key='birth date',
                        path={
                            'day': "./a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./a[starts-with(@href, " \
                                    "'/search/name?birth_year=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='birth notes',
                        path="./a[starts-with(@href, " \
                                "'/search/name?birth_place=')]/text()")]
    _death_attrs = [Attribute(key='death date',
                        path={
                            'day': "./a[starts-with(@href, " \
                                    "'/date/')]/text()",
                            'year': "./a[starts-with(@href, " \
                                    "'/search/name?death_date=')]/text()"
                            },
                        postprocess=build_date),
                    Attribute(key='death notes',
                        path="./text()",
                        # TODO: check if this slicing is always correct
                        postprocess=lambda x: u''.join(x).strip()[2:])]
    extractors = [
            Extractor(label='birth info',
                        path="//div[h5='Date of Birth']",
                        attrs=_birth_attrs),
            Extractor(label='death info',
                        path="//div[h5='Date of Death']",
                        attrs=_death_attrs),
            Extractor(label='nick names',
                        path="//div[h5='Nickname']",
                        attrs=Attribute(key='nick names',
                            path="./text()",
                            joiner='|',
                            postprocess=lambda x: [n.strip().replace(' (',
                                    '::(', 1) for n in x.split('|')
                                    if n.strip()])),
            Extractor(label='birth name',
                        path="//div[h5='Birth Name']",
                        attrs=Attribute(key='birth name',
                            path="./text()",
                            postprocess=lambda x: canonicalName(x.strip()))),
            Extractor(label='height',
                        path="//div[h5='Height']",
                        attrs=Attribute(key='height',
                            path="./text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='mini biography',
                        path="//div[h5='Mini Biography']",
                        attrs=Attribute(key='mini biography',
                            multi=True,
                            path={
                                'bio': "./p//text()",
                                'by': "./b/following-sibling::a/text()"
                                },
                            postprocess=lambda x: "%s::%s" % \
                                (x.get('bio').strip(),
                                (x.get('by') or u'').strip() or u'Anonymous'))),
            Extractor(label='spouse',
                        path="//div[h5='Spouse']/table/tr",
                        attrs=Attribute(key='spouse',
                            multi=True,
                            path={
                                'name': "./td[1]//text()",
                                'info': "./td[2]//text()"
                                },
                            postprocess=lambda x: ("%s::%s" % \
                                (x.get('name').strip(),
                                (x.get('info') or u'').strip())).strip(':'))),
            Extractor(label='trade mark',
                        path="//div[h5='Trade Mark']/p",
                        attrs=Attribute(key='trade mark',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='trivia',
                        path="//div[h5='Trivia']/p",
                        attrs=Attribute(key='trivia',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='quotes',
                        path="//div[h5='Personal Quotes']/p",
                        attrs=Attribute(key='quotes',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            Extractor(label='salary',
                        path="//div[h5='Salary']/table/tr",
                        attrs=Attribute(key='salary history',
                            multi=True,
                            path={
                                'title': "./td[1]//text()",
                                'info': "./td[2]/text()",
                                },
                            postprocess=lambda x: "%s::%s" % \
                                    (x.get('title').strip(),
                                        x.get('info').strip()))),
            Extractor(label='where now',
                        path="//div[h5='Where Are They Now']/p",
                        attrs=Attribute(key='where now',
                            multi=True,
                            path=".//text()",
                            postprocess=lambda x: x.strip())),
            ]

    preprocessors = [
        (re.compile('(<h5>)', re.I), r'</div><div class="_imdbpy">\1'),
        (re.compile('(</table>\n</div>\s+)</div>', re.I + re.DOTALL), r'\1'),
        (re.compile('(<div id="tn15bot">)'), r'</div>\1'),
        (re.compile('\.<br><br>([^\s])', re.I), r'. \1')
        ]

    def postprocess_data(self, data):
        for what in 'birth date', 'death date':
            if what in data and not data[what]:
                del data[what]
        return data


class DOMHTMLOtherWorksParser(DOMParserBase):
    """Parser for the "other works" and "agent" pages of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        owparser = DOMHTMLOtherWorksParser()
        result = owparser.parse(otherworks_html_string)
    """
    _defGetRefs = True
    kind = 'other works'

    # XXX: looks like the 'agent' page is no more public.
    extractors = [
            Extractor(label='other works',
                        path="//h5[text()='Other works']/" \
                                "following-sibling::div[1]",
                        attrs=Attribute(key='self.kind',
                            path=".//text()",
                            postprocess=lambda x: x.strip().split('\n\n')))
            ]

    preprocessors = [
        (re.compile('(<h5>[^<]+</h5>)', re.I),
            r'</div>\1<div class="_imdbpy">'),
        (re.compile('(</table>\n</div>\s+)</div>', re.I), r'\1'),
        (re.compile('(<div id="tn15bot">)'), r'</div>\1'),
        (re.compile('<br/><br/>', re.I), r'\n\n')
        ]


def _build_episode(link, title, minfo, role, roleA, roleAID):
    """Build an Movie object for a given episode of a series."""
    episode_id = analyze_imdbid(link)
    notes = u''
    minidx = minfo.find(' -')
    # Sometimes, for some unknown reason, the role is left in minfo.
    if minidx != -1:
        slfRole = minfo[minidx+3:].lstrip()
        minfo = minfo[:minidx].rstrip()
        if slfRole.endswith(')'):
            commidx = slfRole.rfind('(')
            if commidx != -1:
                notes = slfRole[commidx:]
                slfRole = slfRole[:commidx]
        if slfRole and role is None and roleA is None:
            role = slfRole
    eps_data = analyze_title(title)
    eps_data['kind'] = u'episode'
    # FIXME: it's wrong for multiple characters (very rare on tv series?).
    if role is None:
        role = roleA # At worse, it's None.
    if role is None:
        roleAID = None
    if roleAID is not None:
        roleAID = analyze_imdbid(roleAID)
    e = Movie(movieID=episode_id, data=eps_data, currentRole=role,
            roleID=roleAID, notes=notes)
    # XXX: are we missing some notes?
    # XXX: does it parse things as "Episode dated 12 May 2005 (12 May 2005)"?
    if minfo.startswith('('):
        pe = minfo.find(')')
        if pe != -1:
            date = minfo[1:pe]
            if date != '????':
                e['original air date'] = date
                if eps_data.get('year', '????') == '????':
                    syear = date.split()[-1]
                    if syear.isdigit():
                        e['year'] = int(syear)
    return e


class DOMHTMLSeriesParser(DOMParserBase):
    """Parser for the "by TV series" page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = DOMHTMLSeriesParser()
        result = sparser.parse(filmoseries_html_string)
    """
    _containsObjects = True

    extractors = [
            Extractor(label='series',
                        group="//div[@class='filmo']/span[1]",
                        group_key="./a[1]",
                        path="./following-sibling::ol[1]/li/a[1]",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./@href",
                                'title': "./text()",
                                'info': "./following-sibling::text()",
                                'role': "./following-sibling::i[1]/text()",
                                'roleA': "./following-sibling::a[1]/text()",
                                'roleAID': "./following-sibling::a[1]/@href"
                                },
                            postprocess=lambda x: _build_episode(x.get('link'),
                                x.get('title'),
                                (x.get('info') or u'').strip(),
                                x.get('role'),
                                x.get('roleA'),
                                x.get('roleAID'))))
            ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        nd = {}
        for key in data.keys():
            dom = self.get_dom(key)
            link = self.xpath(dom, "//a/@href")[0]
            title = self.xpath(dom, "//a/text()")[0][1:-1]
            series = Movie(movieID=analyze_imdbid(link),
                           data=analyze_title(title),
                           accessSystem=self._as, modFunct=self._modFunct)
            nd[series] = []
            for episode in data[key]:
                # XXX: should we create a copy of 'series', to avoid
                #      circular references?
                episode['episode of'] = series
                nd[series].append(episode)
        return {'episodes': nd}


class DOMHTMLPersonGenresParser(DOMParserBase):
    """Parser for the "by genre" and "by keywords" pages of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        gparser = DOMHTMLPersonGenresParser()
        result = gparser.parse(bygenre_html_string)
    """
    kind = 'genres'
    _containsObjects = True

    extractors = [
            Extractor(label='genres',
                        group="//b/a[@name]/following-sibling::a[1]",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../../following-sibling::ol[1]/li//a[1]",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={
                                'link': "./@href",
                                'title': "./text()",
                                'info': "./following-sibling::text()"
                                },
                            postprocess=lambda x: \
                                    build_movie(x.get('title') + \
                                    x.get('info').split('[')[0],
                                    analyze_imdbid(x.get('link')))))
            ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        return {self.kind: data}


from movieParser import _parse_merchandising_link

class DOMHTMLPersonSalesParser(DOMParserBase):
    """Parser for the "merchandising links" page of a given person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = DOMHTMLPersonSalesParser()
        result = sparser.parse(sales_html_string)
    """
    extractors = [
        Extractor(label='merchandising links',
                    group="//span[@class='merch_title']",
                    group_key=".//text()",
                    path="./following-sibling::table[1]/" \
                            "/td[@class='w_rowtable_colshop']//tr[1]",
                    attrs=Attribute(key=None,
                        multi=True,
                        path={
                            'link': "./td[2]/a[1]/@href",
                            'text': "./td[1]/img[1]/@alt",
                            'cover': "./ancestor::td[1]/../" \
                                    "td[1]/a[1]/img[1]/@src",
                            },
                        postprocess=_parse_merchandising_link)),
    ]

    preprocessors = [
        (re.compile('(<a name="[^"]+" )/>', re.I), r'\1></a>')
        ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        return {'merchandising links': data}


from movieParser import DOMHTMLTechParser
from movieParser import DOMHTMLOfficialsitesParser
from movieParser import DOMHTMLAwardsParser
from movieParser import DOMHTMLNewsParser


_OBJECTS = {
    'maindetails_parser': ((DOMHTMLMaindetailsParser,), None),
    'bio_parser': ((DOMHTMLBioParser,), None),
    'otherworks_parser': ((DOMHTMLOtherWorksParser,), None),
    #'agent_parser': ((DOMHTMLOtherWorksParser,), {'kind': 'agent'}),
    'person_officialsites_parser': ((DOMHTMLOfficialsitesParser,), None),
    'person_awards_parser': ((DOMHTMLAwardsParser,), {'subject': 'name'}),
    'publicity_parser': ((DOMHTMLTechParser,), {'kind': 'publicity'}),
    'person_series_parser': ((DOMHTMLSeriesParser,), None),
    'person_contacts_parser': ((DOMHTMLTechParser,), {'kind': 'contacts'}),
    'person_genres_parser': ((DOMHTMLPersonGenresParser,), None),
    'person_keywords_parser': ((DOMHTMLPersonGenresParser,),
                                {'kind': 'keywords'}),
    'news_parser': ((DOMHTMLNewsParser,), None),
    'sales_parser': ((DOMHTMLPersonSalesParser,), None)
}

