"""
parser.http.movieParser module (imdb package).

This module provides the classes (and the instances), used to parse the
IMDb pages on the akas.imdb.com server about a movie.
E.g., for Brian De Palma's "The Untouchables", the referred
pages would be:
    combined details:   http://akas.imdb.com/title/tt0094226/combined
    plot summary:       http://akas.imdb.com/title/tt0094226/plotsummary
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
import urllib

from imdb import imdbURL_base
from imdb.Person import Person
from imdb.Movie import Movie
from imdb.Company import Company
from imdb.utils import analyze_title, split_company_name_notes, _Container
from utils import build_person, DOMParserBase, Attribute, Extractor, \
                    analyze_imdbid


# Dictionary used to convert some section's names.
_SECT_CONV = {
        'directed': 'director',
        'directed by': 'director',
        'directors': 'director',
        'editors': 'editor',
        'writing credits': 'writer',
        'writers': 'writer',
        'produced': 'producer',
        'cinematography': 'cinematographer',
        'film editing': 'editor',
        'casting': 'casting director',
        'costume design': 'costume designer',
        'makeup department': 'make up',
        'production management': 'production manager',
        'second unit director or assistant director': 'assistant director',
        'costume and wardrobe department': 'costume department',
        'sound department': 'sound crew',
        'stunts':   'stunt performer',
        'other crew': 'miscellaneous crew',
        'also known as': 'akas',
        'country':  'countries',
        'runtime':  'runtimes',
        'language': 'languages',
        'certification':    'certificates',
        'genre': 'genres',
        'created': 'creator',
        'creators': 'creator',
        'color': 'color info',
        'plot': 'plot outline',
        'seasons': 'number of seasons',
        'art directors': 'art direction',
        'assistant directors': 'assistant director',
        'set decorators': 'set decoration',
        'visual effects department': 'visual effects',
        'production managers': 'production manager',
        'miscellaneous': 'miscellaneous crew',
        'make up department': 'make up',
        'plot summary': 'plot outline',
        'cinematographers': 'cinematographer',
        'camera department': 'camera and electrical department',
        'costume designers': 'costume designer',
        'production designers': 'production design',
        'production managers': 'production manager',
        'music original': 'original music',
        'casting directors': 'casting director',
        'other companies': 'miscellaneous companies',
        'producers': 'producer',
        'special effects by': 'special effects department',
        'special effects': 'special effects companies'
        }


def _manageRoles(mo):
    """Perform some transformation on the html, so that roleIDs can
    be easily retrieved."""
    firstHalf = mo.group(1)
    secondHalf = mo.group(2)
    newRoles = []
    roles = secondHalf.split(' / ')
    for role in roles:
        role = role.strip()
        if not role:
            continue
        roleID = analyze_imdbid(role)
        if roleID is None:
            roleID = u'/'
        else:
            roleID += u'/'
        newRoles.append(u'<div class="_imdbpyrole" roleid="%s">%s</div>' % \
                (roleID, role.strip()))
    return firstHalf + u' / '.join(newRoles) + mo.group(3)


_reRolesMovie = re.compile(r'(<td class="char">)(.*?)(</td>)',
                            re.I | re.M | re.S)

def _replaceBR(mo):
    """Replaces <br> tags with '::' (useful for some akas)"""
    txt = mo.group(0)
    return txt.replace('<br>', '::')

_reAkas = re.compile(r'<h5>also known as:</h5>.*?</div>', re.I | re.M | re.S)

def makeSplitter(lstrip=None, sep='|', comments=True,
                origNotesSep=' (', newNotesSep='::(', strip=None):
    """Return a splitter function suitable for a given set of data."""
    def splitter(x):
        if not x: return x
        x = x.strip()
        if not x: return x
        if lstrip is not None:
            x = x.lstrip(lstrip).lstrip()
        lx = x.split(sep)
        lx[:] = filter(None, [j.strip() for j in lx])
        if comments:
            lx[:] = [j.replace(origNotesSep, newNotesSep, 1) for j in lx]
        if strip:
            lx[:] = [j.strip(strip) for j in lx]
        return lx
    return splitter


def _toInt(val, replace=()):
    """Return the value, converted to integer, or None; if present, 'replace'
    must be a list of tuples of values to replace."""
    for before, after in replace:
        val = val.replace(before, after)
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


class DOMHTMLMovieParser(DOMParserBase):
    """Parser for the "combined details" (and if instance.mdparse is
    True also for the "main details") page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        mparser = DOMHTMLMovieParser()
        result = mparser.parse(combined_details_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='title',
                            path="//h1",
                            attrs=Attribute(key='title',
                                        path=".//text()",
                                        postprocess=analyze_title)),

                Extractor(label='glossarysections',
                        group="//a[@class='glossary']",
                        group_key="./@name",
                        group_key_normalize=lambda x: x.replace('_', ' '),
                        path="../../../..//tr",
                        attrs=Attribute(key=None,
                            multi=True,
                            path={'person': ".//text()",
                                    'link': "./td[1]/a[@href]/@href"},
                            postprocess=lambda x: \
                                    build_person(x.get('person') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                )),

                Extractor(label='cast',
                        path="//table[@class='cast']//tr",
                        attrs=Attribute(key="cast",
                            multi=True,
                            path={'person': ".//text()",
                                'link': "td[2]/a/@href",
                                'roleID': \
                                    "td[4]/div[@class='_imdbpyrole']/@roleid"},
                            postprocess=lambda x: \
                                    build_person(x.get('person') or u'',
                                    personID=analyze_imdbid(x.get('link')),
                                    roleID=(x.get('roleID') or u'').split('/'))
                                )),

                Extractor(label='genres',
                        path="//div[@class='info']//a[starts-with(@href," \
                                " '/Sections/Genres')]",
                        attrs=Attribute(key="genres",
                            multi=True,
                            path="./text()")),

                Extractor(label='h5sections',
                        path="//div[@class='info']/h5/..",
                        attrs=[
                            Attribute(key="plot summary",
                                path="./h5[starts-with(text(), " \
                                        "'Plot:')]/../div/text()",
                                postprocess=lambda x: \
                                        x.strip().rstrip('|').rstrip()),
                            Attribute(key="aspect ratio",
                                path="./h5[starts-with(text()," \
                                        " 'Aspect')]/../div/text()",
                                postprocess=lambda x: x.strip()),
                            Attribute(key="mpaa",
                                path="./h5/a[starts-with(text()," \
                                        " 'MPAA')]/../../div/text()",
                                postprocess=lambda x: x.strip()),
                            Attribute(key="countries",
                                path="./h5[starts-with(text(), " \
                                        "'Countr')]/..//a/text()",
                                    postprocess=makeSplitter(sep='\n')),
                            Attribute(key="language",
                                path="./h5[starts-with(text(), " \
                                        "'Language')]/..//text()",
                                    postprocess=makeSplitter('Language:')),
                            Attribute(key='color info',
                                path="./h5[starts-with(text(), " \
                                        "'Color')]/..//text()",
                                postprocess=makeSplitter('Color:')),
                            Attribute(key='sound mix',
                                path="./h5[starts-with(text(), " \
                                        "'Sound Mix')]/..//text()",
                                postprocess=makeSplitter('Sound Mix:')),
                            # Collects akas not encosed in <i> tags.
                            Attribute(key='other akas',
                                path="./h5[starts-with(text(), " \
                                        "'Also Known As')]/../div//text()",
                                postprocess=makeSplitter(sep='::',
                                                origNotesSep='" - ',
                                                newNotesSep='::',
                                                strip='"')),
                            Attribute(key='runtimes',
                                path="./h5[starts-with(text(), " \
                                        "'Runtime')]/../div/text()",
                                postprocess=makeSplitter()),
                            Attribute(key='certificates',
                                path="./h5[starts-with(text(), " \
                                        "'Certificat')]/..//text()",
                                postprocess=makeSplitter('Certification:')),
                            Attribute(key='number of seasons',
                                path="./h5[starts-with(text(), " \
                                        "'Seasons')]/..//text()",
                                postprocess=lambda x: x.count('|') + 1),
                            Attribute(key='original air date',
                                path="./h5[starts-with(text(), " \
                                        "'Original Air Date')]/../div/text()"),
                            Attribute(key='tv series link',
                                path="./h5[starts-with(text(), " \
                                        "'TV Series')]/..//a/@href"),
                            Attribute(key='tv series title',
                                path="./h5[starts-with(text(), " \
                                        "'TV Series')]/..//a/text()")
                            ]),

                Extractor(label='creator',
                            path="//h5[starts-with(text(), 'Creator')]/..//a",
                            attrs=Attribute(key='creator', multi=True,
                                    path={'name': "./text()",
                                        'link': "./@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='thin writer',
                            path="//h5[starts-with(text(), 'Writer')]/..//a",
                            attrs=Attribute(key='thin writer', multi=True,
                                    path={'name': "./text()",
                                        'link': "./@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='thin director',
                            path="//h5[starts-with(text(), 'Director')]/..//a",
                            attrs=Attribute(key='thin director', multi=True,
                                    path={'name': "./text()",
                                        'link': "@href"},
                                    postprocess=lambda x: \
                                        build_person(x.get('name') or u'',
                                        personID=analyze_imdbid(x.get('link')))
                                    )),

                Extractor(label='top 250/bottom 100',
                            path="//div[@class='starbar-special']/" \
                                    "a[starts-with(@href, '/chart/')]",
                            attrs=Attribute(key='top/bottom rank',
                                            path="./text()")),

                Extractor(label='series years',
                            path="//div[@id='tn15title']//span" \
                                "[starts-with(text(), 'TV series')]",
                            attrs=Attribute(key='series years',
                                    path="./text()",
                                    postprocess=lambda x: \
                                            x.replace('TV series','').strip())),

                Extractor(label='number of episodes',
                            path="//a[@title='Full Episode List']",
                            attrs=Attribute(key='number of episodes',
                                    path="./text()",
                                    postprocess=lambda x: \
                                            _toInt(x, [(' Episodes', '')]))),

                Extractor(label='akas',
                        path="//i[@class='transl']",
                        attrs=Attribute(key='akas', multi=True, path='text()',
                                postprocess=lambda x:
                                x.replace('  ', ' ').rstrip('-').replace('" - ',
                                    '"::', 1).strip('"').replace('  ', ' '))),

                Extractor(label='production notes/status',
                        path="//div[@class='info inprod']",
                        attrs=Attribute(key='production notes',
                                path=".//text()",
                                postprocess=lambda x: x.strip())),

                Extractor(label='blackcatheader',
                        group="//b[@class='blackcatheader']",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="../ul/li",
                        attrs=Attribute(key=None,
                                multi=True,
                                path={'name': "./a//text()",
                                        'comp-link': "./a/@href",
                                        'notes': "./text()"},
                                postprocess=lambda x: \
                                        Company(name=x.get('name') or u'',
                                companyID=analyze_imdbid(x.get('comp-link')),
                                notes=(x.get('notes') or u'').strip())
                            )),

                Extractor(label='rating',
                        path="//div[@class='starbar-meta']/b",
                        attrs=Attribute(key='rating',
                                        path=".//text()")),

                Extractor(label='votes',
                        path="//div[@class='starbar-meta']/a[@href]",
                        attrs=Attribute(key='votes',
                                        path=".//text()")),

                Extractor(label='cover url',
                        path="//a[@name='poster']",
                        attrs=Attribute(key='cover url',
                                        path="./img/@src"))
                ]

    preprocessors = [
        (re.compile(r'(<b class="blackcatheader">.+?</b>)', re.I),
            r'</div><div>\1'),
        ('<small>Full cast and crew for<br></small>', ''),
        ('<td> </td>', '<td>...</td>'),
        ('<span class="tv-extra">TV mini-series</span>',
            '<span class="tv-extra">(mini)</span>'),
        (_reRolesMovie, _manageRoles),
        (_reAkas, _replaceBR)]

    def preprocess_dom(self, dom):
        # Handle series information.
        xpath = self.xpath(dom, "//b[text()='Series Crew']")
        if xpath:
            b = xpath[-1] # In doubt, take the last one.
            for a in self.xpath(b, "./following::h5/a[@class='glossary']"):
                name = a.get('name')
                if name:
                    a.set('name', 'series %s' % name)
        # Remove links to IMDbPro.
        for proLink in self.xpath(dom, "//span[@class='pro-link']"):
            proLink.drop_tree()
        # Remove some 'more' links (keep others, like the one around
        # the number of votes).
        for tn15more in self.xpath(dom,
                    "//a[@class='tn15more'][starts-with(@href, '/title/')]"):
            tn15more.drop_tree()
        return dom

    re_space = re.compile(r'\s+')
    re_airdate = re.compile(r'(.*)\s*\(season (\d+), episode (\d+)\)', re.I)
    def postprocess_data(self, data):
        # Convert section names.
        for sect in data.keys():
            if sect in _SECT_CONV:
                data[_SECT_CONV[sect]] = data[sect]
                del data[sect]
                sect = _SECT_CONV[sect]
        # Filter out fake values.
        for key in data:
            value = data[key]
            if isinstance(value, list) and value:
                if isinstance(value[0], Person):
                    data[key] = filter(lambda x: x.personID is not None, value)
                if isinstance(value[0], _Container):
                    for obj in data[key]:
                        obj.accessSystem = self._as
                        obj.modFunct = self._modFunct
        if 'akas' in data or 'other akas' in data:
            akas = data.get('akas') or []
            other_akas = data.get('other akas') or []
            akas += other_akas
            if 'akas' in data:
                del data['akas']
            if 'other akas' in data:
                del data['other akas']
            if akas:
                data['akas'] = akas
        if 'runtimes' in data:
            data['runtimes'] = [x.replace(' min', u'')
                                for x in data['runtimes']]
        if 'production notes' in data:
            pn = data['production notes'].replace('\n\nComments:',
                                '\nComments:').replace('\n\nNote:',
                                '\nNote:').replace('Note:\n\n',
                                'Note:\n').split('\n')
            for k, v in zip(pn[::2], pn[1::2]):
                v = v.strip()
                if not v:
                    continue
                k = k.lower().strip(':')
                if k == 'note':
                    k = 'status note'
                data[k] = v
            del data['production notes']
        if 'original air date' in data:
            oid = self.re_space.sub(' ', data['original air date']).strip()
            data['original air date'] = oid
            aid = self.re_airdate.findall(oid)
            if aid and len(aid[0]) == 3:
                date, season, episode = aid[0]
                date = date.strip()
                try: season = int(season)
                except: pass
                try: episode = int(episode)
                except: pass
                if date and date != '????':
                    data['original air date'] = date
                else:
                    del data['original air date']
                # Handle also "episode 0".
                if season or type(season) is type(0):
                    data['season'] = season
                if episode or type(season) is type(0):
                    data['episode'] = episode
        for k in ('writer', 'director'):
            t_k = 'thin %s' % k
            if t_k not in data:
                continue
            if k not in data:
                data[k] = data[t_k]
            del data[t_k]
        if 'top/bottom rank' in data:
            tbVal = data['top/bottom rank'].lower()
            if tbVal.startswith('top'):
                tbKey = 'top 250 rank'
                tbVal = _toInt(tbVal, [('top 250: #', '')])
            else:
                tbKey = 'bottom 100 rank'
                tbVal = _toInt(tbVal, [('bottom 100: #', '')])
            if tbVal:
                data[tbKey] = tbVal
            del data['top/bottom rank']
        if 'year' in data and data['year'] == '????':
            del data['year']
        if 'tv series link' in data:
            if 'tv series title' in data:
                data['episode of'] = Movie(title=data['tv series title'],
                                            movieID=analyze_imdbid(
                                                    data['tv series link']),
                                            accessSystem=self._as,
                                            modFunct=self._modFunct)
                del data['tv series title']
            del data['tv series link']
        if 'rating' in data:
            try:
                data['rating'] = float(data['rating'].replace('/10', ''))
            except (TypeError, ValueError):
                pass
        if 'votes' in data:
            try:
                votes = data['votes'].replace(',', '').replace('votes', '')
                data['votes'] = int(votes)
            except (TypeError, ValueError):
                pass
        return data


def _process_plotsummary(x):
    """Process a plot (contributed by Rdian06)."""
    xauthor = x.get('author')
    if xauthor:
        xauthor = xauthor.replace('{', '<').replace('}', '>').replace('(',
                                    '<').replace(')', '>').strip()
    xplot = x.get('plot', u'').strip()
    if xauthor:
        xplot += u'::%s' % xauthor
    return xplot

class DOMHTMLPlotParser(DOMParserBase):
    """Parser for the "plot summary" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a 'plot' key, containing a list
    of string with the structure: 'summary::summary_author <author@email>'.

    Example:
        pparser = HTMLPlotParser()
        result = pparser.parse(plot_summary_html_string)
    """
    _defGetRefs = True

    # Notice that recently IMDb started to put the email of the
    # author only in the link, that we're not collecting, here.
    extractors = [Extractor(label='plot',
                    path="//p[@class='plotpar']",
                    attrs=Attribute(key='plot',
                            multi=True,
                            path={'plot': './text()',
                                'author': './i/a/text()'},
                            postprocess=_process_plotsummary))]


def _process_award(x):
    award = {}
    award['year'] = x.get('year').strip()
    if award['year'] and award['year'].isdigit():
        award['year'] = int(award['year'])
    award['result'] = x.get('result').strip()
    award['award'] = x.get('award').strip()
    category = x.get('category').strip()
    if category:
        award['category'] = category
    received_with = x.get('with')
    if received_with is not None:
        award['with'] = received_with.strip()
    notes = x.get('notes')
    if notes is not None:
        notes = notes.strip()
        if notes:
            award['notes'] = notes
    award['anchor'] = x.get('anchor')
    return award



class DOMHTMLAwardsParser(DOMParserBase):
    """Parser for the "awards" page of a given person or movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        awparser = HTMLAwardsParser()
        result = awparser.parse(awards_html_string)
    """
    subject = 'title'
    _containsObjects = True

    extractors = [
        Extractor(label='awards',
            group="//table//big",
            group_key="./a",
            path="./ancestor::tr[1]/following-sibling::tr/" \
                    "td[last()][not(@colspan)]",
            attrs=Attribute(key=None,
                multi=True,
                path={
                    'year': "../td[1]/a/text()",
                    'result': "../td[2]/b/text()",
                    'award': "../td[3]/text()",
                    'category': "./text()[1]",
                    # FIXME: takes only the first co-recipient
                    'with': "./small[starts-with(text()," \
                            " 'Shared with:')]/following-sibling::a[1]/text()",
                    'notes': "./small[last()]//text()",
                    'anchor': ".//text()"
                    },
                postprocess=_process_award
                )),
        Extractor(label='recipients',
            group="//table//big",
            group_key="./a",
            path="./ancestor::tr[1]/following-sibling::tr/" \
                    "td[last()]/small[1]/preceding-sibling::a",
            attrs=Attribute(key=None,
                multi=True,
                path={
                    'name': "./text()",
                    'link': "./@href",
                    'anchor': "..//text()"
                    }
                ))
    ]

    preprocessors = [
        (re.compile('(<tr><td[^>]*>.*?</td></tr>\n\n</table>)', re.I),
         r'\1</table>'),
        (re.compile('(<tr><td[^>]*>\n\n<big>.*?</big></td></tr>)', re.I),
         r'</table><table class="_imdbpy">\1'),
        (re.compile('(<table[^>]*>\n\n)</table>(<table)', re.I), r'\1\2'),
        (re.compile('(<small>.*?)<br>(.*?</small)', re.I), r'\1 \2'),
        (re.compile('(</tr>\n\n)(<td)', re.I), r'\1<tr>\2')
        ]

    def preprocess_dom(self, dom):
        """Repeat td elements according to their rowspan attributes
        in subsequent tr elements.
        """
        cols = self.xpath(dom, "//td[@rowspan]")
        for col in cols:
            span = int(col.get('rowspan'))
            del col.attrib['rowspan']
            position = len(self.xpath(col, "./preceding-sibling::td"))
            row = col.getparent()
            for tr in self.xpath(row, "./following-sibling::tr")[:span-1]:
                # if not cloned, child will be moved to new parent
                clone = self.clone(col)
                # XXX: beware that here we don't use an "adapted" function,
                #      because both BeautifulSoup and lxml uses the same
                #      "insert" method.
                tr.insert(position, clone)
        return dom

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        nd = []
        for key in data.keys():
            dom = self.get_dom(key)
            assigner = self.xpath(dom, "//a/text()")[0]
            for entry in data[key]:
                if not entry.has_key('name'):
                    # this is an award, not a recipient
                    entry['assigner'] = assigner.strip()
                    # find the recipients
                    matches = [p for p in data[key]
                               if p.has_key('name') and (entry['anchor'] ==
                                   p['anchor'])]
                    if self.subject == 'title':
                        recipients = [Person(name=recipient['name'],
                                    personID=analyze_imdbid(recipient['link']))
                                    for recipient in matches]
                        entry['to'] = recipients
                    elif self.subject == 'name':
                        recipients = [Movie(title=recipient['name'],
                                    movieID=analyze_imdbid(recipient['link']))
                                    for recipient in matches]
                        entry['for'] = recipients
                    nd.append(entry)
                del entry['anchor']
        return {'awards': nd}


class DOMHTMLTaglinesParser(DOMParserBase):
    """Parser for the "taglines" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = DOMHTMLTaglinesParser()
        result = tparser.parse(taglines_html_string)
    """
    extractors = [Extractor(label='taglines',
                            path="//div[@id='tn15content']/p",
                            attrs=Attribute(key='taglines', multi=True,
                                            path="./text()"))]


class DOMHTMLKeywordsParser(DOMParserBase):
    """Parser for the "keywords" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        kwparser = DOMHTMLKeywordsParser()
        result = kwparser.parse(keywords_html_string)
    """
    extractors = [Extractor(label='keywords',
                            path="//a[starts-with(@href, '/keyword/')]",
                            attrs=Attribute(key='keywords',
                                            path="./text()", multi=True,
                                            postprocess=lambda x: \
                                                x.lower().replace(' ', '-')))]


class DOMHTMLAlternateVersionsParser(DOMParserBase):
    """Parser for the "alternate versions" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        avparser = HTMLAlternateVersionsParser()
        result = avparser.parse(alternateversions_html_string)
    """
    _defGetRefs = True
    extractors = [Extractor(label='alternate versions',
                            path="//ul[@class='trivia']/li",
                            attrs=Attribute(key='alternate versions',
                                            multi=True,
                                            path=".//text()",
                                            postprocess=lambda x: x.strip()))]


class DOMHTMLTriviaParser(DOMParserBase):
    """Parser for the "trivia" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        avparser = HTMLAlternateVersionsParser()
        result = avparser.parse(alternateversions_html_string)
    """
    _defGetRefs = True
    extractors = [Extractor(label='alternate versions',
                            path="//div[@class='sodatext']",
                            attrs=Attribute(key='trivia',
                                            multi=True,
                                            path=".//text()",
                                            postprocess=lambda x: x.strip()))]

    def preprocess_dom(self, dom):
        # Remove "link this quote" links.
        for qLink in self.xpath(dom, "//span[@class='linksoda']"):
            qLink.drop_tree()
        return dom



class DOMHTMLSoundtrackParser(DOMHTMLAlternateVersionsParser):
    kind = 'soundtrack'

    preprocessors = [
        ('<br>', '\n')
        ]

    def postprocess_data(self, data):
        if 'soundtrack' in data:
            nd = []
            for x in data['soundtrack']:
                ds = x.split('\n')
                title = ds[0]
                if title[0] == '"' and title[-1] == '"':
                    title = title[1:-1]
                nds = []
                newData = {}
                for l in ds[1:]:
                    if ' with ' in l or ' by ' in l or ' from ' in l \
                            or ' of ' in l or l.startswith('From '):
                        nds.append(l)
                    else:
                        if nds:
                            nds[-1] += l
                        else:
                            nds.append(l)
                newData[title] = {}
                for l in nds:
                    skip = False
                    for sep in ('From ',):
                        if l.startswith(sep):
                            fdix = len(sep)
                            kind = l[:fdix].rstrip().lower()
                            info = l[fdix:].lstrip()
                            newData[title][kind] = info
                            skip = True
                    if not skip:
                        for sep in ' with ', ' by ', ' from ', ' of ':
                            fdix = l.find(sep)
                            if fdix != -1:
                                fdix = fdix+len(sep)
                                kind = l[:fdix].rstrip().lower()
                                info = l[fdix:].lstrip()
                                newData[title][kind] = info
                                break
                nd.append(newData)
            data['soundtrack'] = nd
        return data


class DOMHTMLCrazyCreditsParser(DOMParserBase):
    """Parser for the "crazy credits" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        ccparser = DOMHTMLCrazyCreditsParser()
        result = ccparser.parse(crazycredits_html_string)
    """
    _defGetRefs = True

    extractors = [Extractor(label='crazy credits', path="//ul/li/tt",
                            attrs=Attribute(key='crazy credits', multi=True,
                                path=".//text()",
                                postprocess=lambda x: \
                                    x.replace('\n', ' ').replace('  ', ' ')))]


class DOMHTMLGoofsParser(DOMParserBase):
    """Parser for the "goofs" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        gparser = DOMHTMLGoofsParser()
        result = gparser.parse(goofs_html_string)
    """
    _defGetRefs = True

    extractors = [Extractor(label='goofs', path="//ul[@class='trivia']/li",
                    attrs=Attribute(key='goofs', multi=True, path=".//text()",
                        postprocess=lambda x: (x or u'').strip()))]


class DOMHTMLQuotesParser(DOMParserBase):
    """Parser for the "memorable quotes" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        qparser = DOMHTMLQuotesParser()
        result = qparser.parse(quotes_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='quotes',
            path="//div[@class='_imdbpy']",
            attrs=Attribute(key='quotes',
                multi=True,
                path=".//text()",
                postprocess=lambda x: x.strip().replace(' \n',
                            '::').replace('::\n', '::').replace('\n', ' ')))
        ]

    preprocessors = [
        (re.compile('(<a name="?qt[0-9]{7}"?></a>)', re.I),
            r'\1<div class="_imdbpy">'),
        (re.compile('<hr width="30%">', re.I), '</div>'),
        (re.compile('<hr/>', re.I), '</div>'),
        (re.compile('<script.*?</script>', re.I|re.S), ''),
        # For BeautifulSoup.
        (re.compile('<!-- sid: t-channel : MIDDLE_CENTER -->', re.I), '</div>')
        ]

    def preprocess_dom(self, dom):
        # Remove "link this quote" links.
        for qLink in self.xpath(dom, "//p[@class='linksoda']"):
            qLink.drop_tree()
        return dom

    def postprocess_data(self, data):
        if 'quotes' not in data:
            return {}
        for idx, quote in enumerate(data['quotes']):
            data['quotes'][idx] = quote.split('::')
        return data


class DOMHTMLReleaseinfoParser(DOMParserBase):
    """Parser for the "release dates" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rdparser = DOMHTMLReleaseinfoParser()
        result = rdparser.parse(releaseinfo_html_string)
    """
    extractors = [Extractor(label='release dates',
                    path="//th[@class='xxxx']/../../tr",
                    attrs=Attribute(key='release dates', multi=True,
                        path={'country': ".//td[1]//text()",
                            'date': ".//td[2]//text()",
                            'notes': ".//td[3]//text()"})),
                Extractor(label='akas',
                    path="//div[@class='_imdbpy_akas']/table/tr",
                    attrs=Attribute(key='akas', multi=True,
                        path={'title': "./td[1]/text()",
                            'countries': "./td[2]/text()"}))]

    preprocessors = [
        (re.compile('(<h5><a name="?akas"?.*</table>)', re.I | re.M | re.S),
            r'<div class="_imdbpy_akas">\1</div>')]

    def postprocess_data(self, data):
        if not ('release dates' in data or 'akas' in data): return data
        releases = data.get('release dates') or []
        rl = []
        for i in releases:
            country = i.get('country')
            date = i.get('date')
            if not (country and date): continue
            country = country.strip()
            date = date.strip()
            if not (country and date): continue
            notes = i['notes']
            info = u'%s::%s' % (country, date)
            if notes:
                info += notes
            rl.append(info)
        if releases:
            del data['release dates']
        if rl:
            data['release dates'] = rl
        akas = data.get('akas') or []
        nakas = []
        for aka in akas:
            title = aka.get('title', '').strip()
            if not title:
                continue
            countries = aka.get('countries', '').split('/')
            if not countries:
                nakas.append(title)
            else:
                for country in countries:
                    nakas.append('%s::%s' % (title, country.strip()))
        if akas:
            del data['akas']
        if nakas:
            data['akas from release info'] = nakas
        return data


class DOMHTMLRatingsParser(DOMParserBase):
    """Parser for the "user ratings" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rparser = DOMHTMLRatingsParser()
        result = rparser.parse(userratings_html_string)
    """
    re_means = re.compile('mean\s*=\s*([0-9]\.[0-9])\.\s*median\s*=\s*([0-9])',
                          re.I)
    extractors = [
        Extractor(label='number of votes',
            path="//td[b='Percentage']/../../tr",
            attrs=[Attribute(key='votes',
                            multi=True,
                            path={
                                'votes': "td[1]//text()",
                                'ordinal': "td[3]//text()"
                                })]),
        Extractor(label='mean and median',
            path="//p[starts-with(text(), 'Arithmetic mean')]",
            attrs=Attribute(key='mean and median',
                            path="text()")),
        Extractor(label='rating',
            path="//a[starts-with(@href, '/search/title?user_rating=')]",
            attrs=Attribute(key='rating',
                            path="text()")),
        Extractor(label='demographic voters',
            path="//td[b='Average']/../../tr",
            attrs=Attribute(key='demographic voters',
                            multi=True,
                            path={
                                'voters': "td[1]//text()",
                                'votes': "td[2]//text()",
                                'average': "td[3]//text()"
                                })),
        Extractor(label='top 250',
            path="//a[text()='top 250']",
            attrs=Attribute(key='top 250',
                            path="./preceding-sibling::text()[1]"))
        ]

    def postprocess_data(self, data):
        nd = {}
        votes = data.get('votes', [])
        if votes:
            nd['number of votes'] = {}
            for i in xrange(1, 11):
                nd['number of votes'][int(votes[i]['ordinal'])] = \
                        int(votes[i]['votes'].replace(',', ''))
        mean = data.get('mean and median', '')
        if mean:
            means = self.re_means.findall(mean)
            if means and len(means[0]) == 2:
                am, med = means[0]
                try: am = float(am)
                except (ValueError, OverflowError): pass
                if type(am) is type(1.0):
                    nd['arithmetic mean'] = am
                try: med = int(med)
                except (ValueError, OverflowError): pass
                if type(med) is type(0):
                    nd['median'] = med
        if 'rating' in data:
            nd['rating'] = float(data['rating'])
        dem_voters = data.get('demographic voters')
        if dem_voters:
            nd['demographic'] = {}
            for i in xrange(1, len(dem_voters)):
                if (dem_voters[i]['votes'] is not None) \
                   and (dem_voters[i]['votes'].strip()):
                    nd['demographic'][dem_voters[i]['voters'].strip().lower()] \
                                = (int(dem_voters[i]['votes'].replace(',', '')),
                            float(dem_voters[i]['average']))
        if 'imdb users' in nd.get('demographic', {}):
            nd['votes'] = nd['demographic']['imdb users'][0]
            nd['demographic']['all votes'] = nd['demographic']['imdb users']
            del nd['demographic']['imdb users']
        top250 = data.get('top 250')
        if top250:
            sd = top250[9:]
            i = sd.find(' ')
            if i != -1:
                sd = sd[:i]
                try: sd = int(sd)
                except (ValueError, OverflowError): pass
                if type(sd) is type(0):
                    nd['top 250 rank'] = sd
        return nd


class DOMHTMLEpisodesRatings(DOMParserBase):
    """Parser for the "episode ratings ... by date" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        erparser = DOMHTMLEpisodesRatings()
        result = erparser.parse(eprating_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='title', path="//title",
                            attrs=Attribute(key='title', path="./text()")),
                Extractor(label='ep ratings',
                        path="//th/../..//tr",
                        attrs=Attribute(key='episodes', multi=True,
                                path={'nr': ".//td[1]/text()",
                                        'ep title': ".//td[2]//text()",
                                        'movieID': ".//td[2]/a/@href",
                                        'rating': ".//td[3]/text()",
                                        'votes': ".//td[4]/text()"}))]

    def postprocess_data(self, data):
        if 'title' not in data or 'episodes' not in data: return {}
        nd = []
        title = data['title']
        for i in data['episodes']:
            ept = i['ep title']
            movieID = analyze_imdbid(i['movieID'])
            votes = i['votes']
            rating = i['rating']
            if not (ept and movieID and votes and rating): continue
            try:
                votes = int(votes.replace(',', '').replace('.', ''))
            except:
                pass
            try:
                rating = float(rating)
            except:
                pass
            ept = ept.strip()
            ept = u'%s {%s' % (title, ept)
            nr = i['nr']
            if nr:
                ept += u' (#%s)' % nr.strip()
            ept += '}'
            if movieID is not None:
                movieID = str(movieID)
            m = Movie(title=ept, movieID=movieID, accessSystem=self._as,
                        modFunct=self._modFunct)
            epofdict = m.get('episode of')
            if epofdict is not None:
                m['episode of'] = Movie(data=epofdict, accessSystem=self._as,
                        modFunct=self._modFunct)
            nd.append({'episode': m, 'votes': votes, 'rating': rating})
        return {'episodes rating': nd}


def _normalize_href(href):
    if (href is not None) and (not href.lower().startswith('http://')):
        if href.startswith('/'): href = href[1:]
        href = '%s%s' % (imdbURL_base, href)
    return href


class DOMHTMLOfficialsitesParser(DOMParserBase):
    """Parser for the "official sites", "external reviews", "newsgroup
    reviews", "miscellaneous links", "sound clips", "video clips" and
    "photographs" pages of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        osparser = DOMHTMLOfficialsitesParser()
        result = osparser.parse(officialsites_html_string)
    """
    kind = 'official sites'

    extractors = [
        Extractor(label='site',
            path="//ol/li/a",
            attrs=Attribute(key='self.kind',
                multi=True,
                path={
                    'link': "./@href",
                    'info': "./text()"
                },
                postprocess=lambda x: (x.get('info').strip(),
                            urllib.unquote(_normalize_href(x.get('link'))))))
        ]


class DOMHTMLConnectionParser(DOMParserBase):
    """Parser for the "connections" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        connparser = DOMHTMLConnectionParser()
        result = connparser.parse(connections_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='connection',
                    group="//div[@class='_imdbpy']",
                    group_key="./h5/text()",
                    group_key_normalize=lambda x: x.lower(),
                    path="./a",
                    attrs=Attribute(key=None,
                                    path={'title': "./text()",
                                            'movieID': "./@href"},
                                    multi=True))]

    preprocessors = [
        ('<h5>', '</div><div class="_imdbpy"><h5>'),
        # To get the movie's year.
        ('</a> (', ' ('),
        ('\n<br/>', '</a>'),
        ('<br/> - ', '::')
        ]

    def postprocess_data(self, data):
        for key in data.keys():
            nl = []
            for v in data[key]:
                title = v['title']
                ts = title.split('::', 1)
                title = ts[0].strip()
                notes = u''
                if len(ts) == 2:
                    notes = ts[1].strip()
                m = Movie(title=title,
                            movieID=analyze_imdbid(v['movieID']),
                            accessSystem=self._as, notes=notes,
                            modFunct=self._modFunct)
                nl.append(m)
            data[key] = nl
        if not data: return {}
        return {'connections': data}


class DOMHTMLLocationsParser(DOMParserBase):
    """Parser for the "locations" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        lparser = DOMHTMLLocationsParser()
        result = lparser.parse(locations_html_string)
    """
    extractors = [Extractor(label='locations', path="//dt",
                    attrs=Attribute(key='locations', multi=True,
                                path={'place': ".//text()",
                                        'note': "./following-sibling::dd[1]" \
                                                "//text()"},
                                postprocess=lambda x: (u'%s::%s' % (
                                    x['place'].strip(),
                                    (x['note'] or u'').strip())).strip(':')))]


class DOMHTMLTechParser(DOMParserBase):
    """Parser for the "technical", "business", "literature",
    "publicity" (for people) and "contacts (for people) pages of
    a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        tparser = HTMLTechParser()
        result = tparser.parse(technical_html_string)
    """
    kind = 'tech'

    extractors = [Extractor(label='tech',
                        group="//h5",
                        group_key="./text()",
                        group_key_normalize=lambda x: x.lower(),
                        path="./following-sibling::div[1]",
                        attrs=Attribute(key=None,
                                    path=".//text()",
                                    postprocess=lambda x: [t.strip()
                                        for t in x.split('\n') if t.strip()]))]

    preprocessors = [
        (re.compile('(<h5>.*?</h5>)', re.I), r'\1<div class="_imdbpy">'),
        (re.compile('((<br/>|</p>|</table>))\n?<br/>(?!<a)', re.I),
            r'\1</div>'),
        # the ones below are for the publicity parser
        (re.compile('<p>(.*?)</p>', re.I), r'\1<br/>'),
        (re.compile('(</td><td valign="top">)', re.I), r'\1::'),
        (re.compile('(</tr><tr>)', re.I), r'\n\1'),
        # this is for splitting individual entries
        (re.compile('<br/>', re.I), r'\n'),
        ]

    def postprocess_data(self, data):
        for key in data:
            data[key] = filter(None, data[key])
        if self.kind in ('literature', 'business', 'contacts') and data:
            if 'screenplay/teleplay' in data:
                data['screenplay-teleplay'] = data['screenplay/teleplay']
                del data['screenplay/teleplay']
            data = {self.kind: data}
        else:
            if self.kind == 'publicity':
                if 'biography (print)' in data:
                    data['biography-print'] = data['biography (print)']
                    del data['biography (print)']
            # Tech info.
            for key in data.keys():
                if key.startswith('film negative format'):
                    data['film negative format'] = data[key]
                    del data[key]
                elif key.startswith('film length'):
                    data['film length'] = data[key]
                    del data[key]
        return data


class DOMHTMLDvdParser(DOMParserBase):
    """Parser for the "dvd" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        dparser = DOMHTMLDvdParser()
        result = dparser.parse(dvd_html_string)
    """
    _defGetRefs = True
    extractors = [Extractor(label='dvd',
            path="//div[@class='base_layer']",
            attrs=[Attribute(key=None,
                multi=True,
                path={
                    'title': "../table[1]//h3/text()",
                    'cover': "../table[1]//img/@src",
                    'region': ".//p[b='Region:']/text()",
                    'asin': ".//p[b='ASIN:']/text()",
                    'upc': ".//p[b='UPC:']/text()",
                    'rating': ".//p/b[starts-with(text(), 'Rating:')]/../img/@alt",
                    'certificate': ".//p[b='Certificate:']/text()",
                    'runtime': ".//p[b='Runtime:']/text()",
                    'label': ".//p[b='Label:']/text()",
                    'studio': ".//p[b='Studio:']/text()",
                    'release date': ".//p[b='Release Date:']/text()",
                    'dvd format': ".//p[b='DVD Format:']/text()",
                    'dvd features': ".//p[b='DVD Features: ']//text()",
                    'supplements': "..//div[span='Supplements']" \
                            "/following-sibling::div[1]//text()",
                    'review': "..//div[span='Review']/following-sibling::div[1]//text()",
                    'titles':  "..//div[starts-with(text(), 'Titles in this Product')]" \
                            "/..//text()",
                },
                postprocess=lambda x: {
                'title': (x.get('title') or u'').strip(),
                'cover': (x.get('cover') or u'').strip(),
                'region': (x.get('region') or u'').strip(),
                'asin': (x.get('asin') or u'').strip(),
                'upc': (x.get('upc') or u'').strip(),
                'rating': (x.get('rating') or u'Not Rated').strip().replace('Rating: ', ''),
                'certificate': (x.get('certificate') or u'').strip(),
                'runtime': (x.get('runtime') or u'').strip(),
                'label': (x.get('label') or u'').strip(),
                'studio': (x.get('studio') or u'').strip(),
                'release date': (x.get('release date') or u'').strip(),
                'dvd format': (x.get('dvd format') or u'').strip(),
                'dvd features': (x.get('dvd features') or u'').strip().replace('DVD Features: ', ''),
                'supplements': (x.get('supplements') or u'').strip(),
                'review': (x.get('review') or u'').strip(),
                'titles in this product': (x.get('titles') or u'').strip().replace('Titles in this Product::', ''),
                }
                 )])]

    preprocessors = [
        (re.compile('<p>(<table class="dvd_section" .*)</p>\s*<hr\s*/>', re.I),
         r'<div class="_imdbpy">\1</div>'),
        (re.compile('<p>(<div class\s*=\s*"base_layer")', re.I), r'\1'),
        (re.compile('</p>\s*<p>(<div class="dvd_section")', re.I), r'\1'),
        (re.compile('</div><div class="dvd_row(_alt)?">', re.I), r'::')
    ]

    def postprocess_data(self, data):
        if not data:
            return data
        dvds = data['dvd']
        for dvd in dvds:
            if dvd['cover'].find('noposter') != -1:
                del dvd['cover']
            for key in dvd.keys():
                if not dvd[key]:
                    del dvd[key]
            if 'supplements' in dvd:
                dvd['supplements'] = dvd['supplements'].split('::')
        return data


class DOMHTMLRecParser(DOMParserBase):
    """Parser for the "recommendations" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        rparser = HTMLRecParser()
        result = rparser.parse(recommendations_html_string)
    """
    _containsObjects = True

    extractors = [Extractor(label='recommendations',
                    path="//td[@valign='middle'][1]",
                    attrs=Attribute(key='../../tr/td[1]//text()',
                            multi=True,
                            path={'title': ".//text()",
                                    'movieID': ".//a/@href"}))]
    def postprocess_data(self, data):
        for key in data.keys():
            n_key = key
            n_keyl = n_key.lower()
            if n_keyl == 'suggested by the database':
                n_key = 'database'
            elif n_keyl == 'imdb users recommend':
                n_key = 'users'
            data[n_key] = [Movie(title=x['title'],
                        movieID=analyze_imdbid(x['movieID']),
                        accessSystem=self._as, modFunct=self._modFunct)
                        for x in data[key]]
            del data[key]
        if data: return {'recommendations': data}
        return data


class DOMHTMLNewsParser(DOMParserBase):
    """Parser for the "news" page of a given movie or person.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        nwparser = DOMHTMLNewsParser()
        result = nwparser.parse(news_html_string)
    """
    _defGetRefs = True

    extractors = [
        Extractor(label='news',
            path="//h2",
            attrs=Attribute(key='news',
                multi=True,
                path={
                    'title': "./text()",
                    'fromdate': "../following-sibling::p[1]/small//text()",
                    # FIXME: sometimes (see The Matrix (1999)) <p> is found
                    #        inside news text.
                    'body': "../following-sibling::p[2]//text()",
                    'link': "../..//a[text()='Permalink']/@href",
                    'fulllink': "../..//a[starts-with(text(), " \
                            "'See full article at')]/@href"
                    },
                postprocess=lambda x: {
                    'title': x.get('title').strip(),
                    'date': x.get('fromdate').split('|')[0].strip(),
                    'from': x.get('fromdate').split('|')[1].replace('From ',
                            '').strip(),
                    'body': (x.get('body') or u'').strip(),
                    'link': _normalize_href(x.get('link')),
                    'full article link': _normalize_href(x.get('fulllink'))
                }))
        ]

    preprocessors = [
        (re.compile('(<a name=[^>]+><h2>)', re.I), r'<div class="_imdbpy">\1'),
        (re.compile('(<hr/>)', re.I), r'</div>\1'),
        (re.compile('<p></p>', re.I), r'')
        ]

    def postprocess_data(self, data):
        if not data.has_key('news'):
            return {}
        for news in data['news']:
            if news.has_key('full article link'):
                if news['full article link'] is None:
                    del news['full article link']
        return data


def _parse_review(x):
    result = {}
    title = x.get('title').strip()
    if title[-1] == ':': title = title[:-1]
    result['title'] = title
    result['link'] = _normalize_href(x.get('link'))
    kind =  x.get('kind').strip()
    if kind[-1] == ':': kind = kind[:-1]
    result['review kind'] = kind
    text = x.get('review').replace('\n\n', '||').replace('\n', ' ').split('||')
    review = '\n'.join(text)
    if x.get('author') is not None:
        author = x.get('author').strip()
        review = review.split(author)[0].strip()
        result['review author'] = author[2:]
    if x.get('item') is not None:
        item = x.get('item').strip()
        review = review[len(item):].strip()
        review = "%s: %s" % (item, review)
    result['review'] = review
    return result


class DOMHTMLAmazonReviewsParser(DOMParserBase):
    """Parser for the "amazon reviews" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        arparser = DOMHTMLAmazonReviewsParser()
        result = arparser.parse(amazonreviews_html_string)
    """
    extractors = [
        Extractor(label='amazon reviews',
            group="//h3",
            group_key="./a/text()",
            group_key_normalize=lambda x: x[:-1],
            path="./following-sibling::p[1]/span[@class='_review']",
            attrs=Attribute(key=None,
                multi=True,
                path={
                    'title': "../preceding-sibling::h3[1]/a[1]/text()",
                    'link': "../preceding-sibling::h3[1]/a[1]/@href",
                    'kind': "./preceding-sibling::b[1]/text()",
                    'item': "./i/b/text()",
                    'review': ".//text()",
                    'author': "./i[starts-with(text(), '--')]/text()"
                    },
                postprocess=_parse_review))
        ]

    preprocessors = [
        (re.compile('<p>\n(?!<b>)', re.I), r'\n'),
        (re.compile('(\n</b>\n)', re.I), r'\1<span class="_review">'),
        (re.compile('(</p>\n\n)', re.I), r'</span>\1'),
        (re.compile('(\s\n)(<i><b>)', re.I), r'</span>\1<span class="_review">\2')
        ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        nd = []
        for item in data.keys():
            nd = nd + data[item]
        return {'amazon reviews': nd}


def _parse_merchandising_link(x):
    result = {}
    link = x.get('link')
    result['link'] = _normalize_href(link)
    text = x.get('text')
    if text is not None:
        result['link-text'] = text.strip()
    cover = x.get('cover')
    if cover is not None:
        result['cover'] = cover
    description = x.get('description')
    if description is not None:
        shop = x.get('shop')
        if shop is not None:
            result['description'] = u'%s::%s' % (shop, description.strip())
        else:
            result['description'] = description.strip()
    return result


class DOMHTMLSalesParser(DOMParserBase):
    """Parser for the "merchandising links" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = DOMHTMLSalesParser()
        result = sparser.parse(sales_html_string)
    """
    extractors = [
        Extractor(label='shops',
                    group="//h5/a[@name]/..",
                    group_key="./a[1]/text()",
                    group_key_normalize=lambda x: x.lower(),
                    path=".//following-sibling::table[1]/" \
                            "/td[@class='w_rowtable_colshop']//tr[1]",
                    attrs=Attribute(key=None,
                        multi=True,
                        path={
                            'link': "./td[2]/a[1]/@href",
                            'text': "./td[1]/img[1]/@alt",
                            'cover': "./ancestor::td[1]/../td[1]"\
                                    "/a[1]/img[1]/@src",
                            },
                        postprocess=_parse_merchandising_link)),
        Extractor(label='others',
                    group="//span[@class='_info']/..",
                    group_key="./h5/a[1]/text()",
                    group_key_normalize=lambda x: x.lower(),
                    path="./span[@class='_info']",
                    attrs=Attribute(key=None,
                        multi=True,
                        path={
                            'link': "./preceding-sibling::a[1]/@href",
                            'shop': "./preceding-sibling::a[1]/text()",
                            'description': ".//text()",
                            },
                        postprocess=_parse_merchandising_link))
    ]

    preprocessors = [
        (re.compile('(<h5><a name=)', re.I), r'</div><div class="_imdbpy">\1'),
        (re.compile('(</h5>\n<br/>\n)</div>', re.I), r'\1'),
        (re.compile('(<br/><br/>\n)(\n)', re.I), r'\1</div>\2'),
        (re.compile('(\n)(Search.*?)(</a>)(\n)', re.I), r'\3\1\2\4'),
        (re.compile('(\n)(Search.*?)(\n)', re.I),
            r'\1<span class="_info">\2</span>\3')
        ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        return {'merchandising links': data}


def _build_episode(x):
    """Create a Movie object for a given series' episode."""
    episode_id = analyze_imdbid(x.get('link'))
    episode_title = x.get('title')
    e = Movie(movieID=episode_id, title=episode_title)
    e['kind'] = u'episode'
    oad = x.get('oad')
    if oad:
        e['original air date'] = oad.strip()
    year = x.get('year')
    if year is not None:
        year = year[5:]
        if year == 'unknown': year = u'????'
        if year and year.isdigit():
            year = int(year)
        e['year'] = year
    else:
        if oad and oad[-4:].isdigit():
            e['year'] = int(oad[-4:])
    epinfo = x.get('episode')
    if epinfo is not None:
        season, episode = epinfo.split(':')[0].split(',')
        e['season'] = int(season[7:])
        e['episode'] = int(episode[8:])
    else:
        e['season'] = 'unknown'
        e['episode'] = 'unknown'
    plot = x.get('plot')
    if plot:
        e['plot'] = plot.strip()
    return e


class DOMHTMLEpisodesParser(DOMParserBase):
    """Parser for the "episode list" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        eparser = DOMHTMLEpisodesParser()
        result = eparser.parse(episodes_html_string)
    """
    _containsObjects = True

    kind = 'episodes list'
    _episodes_path = "..//h4"
    _oad_path = "./following-sibling::span/strong[1]/text()"

    def _init(self):
        self.extractors = [
            Extractor(label='series',
                path="//html",
                attrs=[Attribute(key='series title',
                                path=".//title/text()"),
                        Attribute(key='series movieID',
                                path=".//h1/a[@class='main']/@href",
                                postprocess=analyze_imdbid)
                    ]),
            Extractor(label='episodes',
                group="//div[@class='_imdbpy']/h3",
                group_key="./a/@name",
                path=self._episodes_path,
                attrs=Attribute(key=None,
                    multi=True,
                    path={
                        'link': "./a/@href",
                        'title': "./a/text()",
                        'year': "./preceding-sibling::a[1]/@name",
                        'episode': "./text()[1]",
                        'oad': self._oad_path,
                        'plot': "./following-sibling::text()[1]"
                    },
                    postprocess=_build_episode))]
        if self.kind == 'episodes cast':
            self.extractors += [
                Extractor(label='cast',
                    group="//h4",
                    group_key="./text()[1]",
                    group_key_normalize=lambda x: x.strip(),
                    path="./following-sibling::table[1]//td[@class='nm']",
                    attrs=Attribute(key=None,
                        multi=True,
                        path={'person': "..//text()",
                            'link': "./a/@href",
                            'roleID': \
                                "../td[4]/div[@class='_imdbpyrole']/@roleid"},
                        postprocess=lambda x: \
                                build_person(x.get('person') or u'',
                                personID=analyze_imdbid(x.get('link')),
                                roleID=(x.get('roleID') or u'').split('/'),
                                accessSystem=self._as,
                                modFunct=self._modFunct)))
                ]

    preprocessors = [
        (re.compile('(<hr/>\n)(<h3>)', re.I),
                    r'</div>\1<div class="_imdbpy">\2'),
        (re.compile('(</p>\n\n)</div>', re.I), r'\1'),
        (re.compile('<h3>(.*?)</h3>', re.I), r'<h4>\1</h4>'),
        (_reRolesMovie, _manageRoles),
        (re.compile('(<br/> <br/>\n)(<hr/>)', re.I), r'\1</div>\2')
        ]

    def postprocess_data(self, data):
        # A bit extreme?
        if not 'series title' in data: return {}
        if not 'series movieID' in data: return {}
        stitle = data['series title'].replace('- Episode list', '')
        stitle = stitle.replace('- Episodes list', '')
        stitle = stitle.replace('- Episode cast', '')
        stitle = stitle.replace('- Episodes cast', '')
        stitle = stitle.strip()
        if not stitle: return {}
        seriesID = data['series movieID']
        if seriesID is None: return {}
        series = Movie(title=stitle, movieID=str(seriesID),
                        accessSystem=self._as, modFunct=self._modFunct)
        nd = {}
        for key in data.keys():
            if key.startswith('season-'):
                season_key = key[7:]
                try: season_key = int(season_key)
                except: pass
                nd[season_key] = {}
                for episode in data[key]:
                    if not episode: continue
                    episode_key = episode.get('episode')
                    if episode_key is None: continue
                    cast_key = 'Season %s, Episode %s:' % (season_key,
                                                            episode_key)
                    if data.has_key(cast_key):
                        cast = data[cast_key]
                        for i in xrange(len(cast)):
                            cast[i].billingPos = i + 1
                        episode['cast'] = cast
                    episode['episode of'] = series
                    nd[season_key][episode_key] = episode
        if len(nd) == 0:
            return {}
        return {'episodes': nd}


class DOMHTMLEpisodesCastParser(DOMHTMLEpisodesParser):
    """Parser for the "episodes cast" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        eparser = DOMHTMLEpisodesParser()
        result = eparser.parse(episodes_html_string)
    """
    kind = 'episodes cast'
    _episodes_path = "..//h4"
    _oad_path = "./following-sibling::b[1]/text()"


class DOMHTMLFaqsParser(DOMParserBase):
    """Parser for the "FAQ" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        fparser = DOMHTMLFaqsParser()
        result = fparser.parse(faqs_html_string)
    """
    _defGetRefs = True

    # XXX: bsoup and lxml don't match (looks like a minor issue, anyway).

    extractors = [
        Extractor(label='faqs',
            path="//div[@class='section']",
            attrs=Attribute(key='faqs',
                multi=True,
                path={
                    'question': "./h3/a/span/text()",
                    'answer': "../following-sibling::div[1]//text()"
                },
                postprocess=lambda x: u'%s::%s' % (x.get('question').strip(),
                                    '\n\n'.join(x.get('answer').replace(
                                        '\n\n', '\n').strip().split('||')))))
        ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||'),
        (re.compile('<h4>(.*?)</h4>\n', re.I), r'||\1--'),
        (re.compile('<span class="spoiler"><span>(.*?)</span></span>', re.I),
         r'[spoiler]\1[/spoiler]')
        ]


class DOMHTMLAiringParser(DOMParserBase):
    """Parser for the "airing" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        aparser = DOMHTMLAiringParser()
        result = aparser.parse(airing_html_string)
    """
    _containsObjects = True

    extractors = [
        Extractor(label='series title',
            path="//title",
            attrs=Attribute(key='series title', path="./text()",
                            postprocess=lambda x: \
                                    x.replace(' - TV schedule', u''))),
        Extractor(label='series id',
            path="//h1/a[@href]",
            attrs=Attribute(key='series id', path="./@href")),

        Extractor(label='tv airings',
            path="//tr[@class]",
            attrs=Attribute(key='airing',
                multi=True,
                path={
                    'date': "./td[1]//text()",
                    'time': "./td[2]//text()",
                    'channel': "./td[3]//text()",
                    'link': "./td[4]/a[1]/@href",
                    'title': "./td[4]//text()",
                    'season': "./td[5]//text()",
                    },
                postprocess=lambda x: {
                    'date': x.get('date'),
                    'time': x.get('time'),
                    'channel': x.get('channel').strip(),
                    'link': x.get('link'),
                    'title': x.get('title'),
                    'season': (x.get('season') or '').strip()
                    }
                ))
    ]

    def postprocess_data(self, data):
        if len(data) == 0:
            return {}
        seriesTitle = data['series title']
        seriesID = analyze_imdbid(data['series id'])
        if data.has_key('airing'):
            for airing in data['airing']:
                title = airing.get('title', '').strip()
                if not title:
                    epsTitle = seriesTitle
                    if seriesID is None:
                        continue
                    epsID = seriesID
                else:
                    epsTitle = '%s {%s}' % (data['series title'],
                                            airing['title'])
                    epsID = analyze_imdbid(airing['link'])
                e = Movie(title=epsTitle, movieID=epsID)
                airing['episode'] = e
                del airing['link']
                del airing['title']
                if not airing['season']:
                    del airing['season']
        if 'series title' in data:
            del data['series title']
        if 'series id' in data:
            del data['series id']
        if 'airing' in data:
            data['airing'] = filter(None, data['airing'])
        if 'airing' not in data or not data['airing']:
            return {}
        return data


class DOMHTMLSynopsisParser(DOMParserBase):
    """Parser for the "synopsis" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        sparser = HTMLSynopsisParser()
        result = sparser.parse(synopsis_html_string)
    """
    extractors = [
        Extractor(label='synopsis',
            path="//div[@class='display'][not(@style)]",
            attrs=Attribute(key='synopsis',
                path=".//text()",
                postprocess=lambda x: '\n\n'.join(x.strip().split('||'))))
    ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||')
        ]


class DOMHTMLParentsGuideParser(DOMParserBase):
    """Parser for the "parents guide" page of a given movie.
    The page should be provided as a string, as taken from
    the akas.imdb.com server.  The final result will be a
    dictionary, with a key for every relevant section.

    Example:
        pgparser = HTMLParentsGuideParser()
        result = pgparser.parse(parentsguide_html_string)
    """
    extractors = [
        Extractor(label='parents guide',
            group="//div[@class='section']",
            group_key="./h3/a/span/text()",
            group_key_normalize=lambda x: x.lower(),
            path="../following-sibling::div[1]/p",
            attrs=Attribute(key=None,
                path=".//text()",
                postprocess=lambda x: [t.strip().replace('\n', ' ')
                                       for t in x.split('||') if t.strip()]))
    ]

    preprocessors = [
        (re.compile('<br/><br/>', re.I), r'||')
        ]

    def postprocess_data(self, data):
        data2 = {}
        for key in data:
            if data[key]:
                data2[key] = data[key]
        if not data2:
            return {}
        return {'parents guide': data2}


_OBJECTS = {
    'movie_parser':  ((DOMHTMLMovieParser,), None),
    'plot_parser':  ((DOMHTMLPlotParser,), None),
    'movie_awards_parser': ((DOMHTMLAwardsParser,), None),
    'taglines_parser':  ((DOMHTMLTaglinesParser,), None),
    'keywords_parser':  ((DOMHTMLKeywordsParser,), None),
    'crazycredits_parser':  ((DOMHTMLCrazyCreditsParser,), None),
    'goofs_parser':  ((DOMHTMLGoofsParser,), None),
    'alternateversions_parser':  ((DOMHTMLAlternateVersionsParser,), None),
    'trivia_parser':  ((DOMHTMLTriviaParser,), None),
    'soundtrack_parser':  ((DOMHTMLSoundtrackParser,), {'kind': 'soundtrack'}),
    'quotes_parser':  ((DOMHTMLQuotesParser,), None),
    'releasedates_parser':  ((DOMHTMLReleaseinfoParser,), None),
    'ratings_parser':  ((DOMHTMLRatingsParser,), None),
    'officialsites_parser':  ((DOMHTMLOfficialsitesParser,), None),
    'externalrev_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'external reviews'}),
    'newsgrouprev_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'newsgroup reviews'}),
    'misclinks_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'misc links'}),
    'soundclips_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'sound clips'}),
    'videoclips_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'video clips'}),
    'photosites_parser':  ((DOMHTMLOfficialsitesParser,),
                            {'kind': 'photo sites'}),
    'connections_parser':  ((DOMHTMLConnectionParser,), None),
    'tech_parser':  ((DOMHTMLTechParser,), None),
    'business_parser':  ((DOMHTMLTechParser,),
                            {'kind': 'business', '_defGetRefs': 1}),
    'literature_parser':  ((DOMHTMLTechParser,), {'kind': 'literature'}),
    'locations_parser':  ((DOMHTMLLocationsParser,), None),
    'dvd_parser':  ((DOMHTMLDvdParser,), None),
    'rec_parser':  ((DOMHTMLRecParser,), None),
    'news_parser':  ((DOMHTMLNewsParser,), None),
    'amazonrev_parser':  ((DOMHTMLAmazonReviewsParser,), None),
    'sales_parser':  ((DOMHTMLSalesParser,), None),
    'episodes_parser':  ((DOMHTMLEpisodesParser,), None),
    'episodes_cast_parser':  ((DOMHTMLEpisodesCastParser,), None),
    'eprating_parser':  ((DOMHTMLEpisodesRatings,), None),
    'movie_faqs_parser':  ((DOMHTMLFaqsParser,), None),
    'airing_parser':  ((DOMHTMLAiringParser,), None),
    'synopsis_parser':  ((DOMHTMLSynopsisParser,), None),
    'parentsguide_parser':  ((DOMHTMLParentsGuideParser,), None)
}

