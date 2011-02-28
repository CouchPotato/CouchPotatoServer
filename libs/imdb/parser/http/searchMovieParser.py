"""
parser.http.searchMovieParser module (imdb package).

This module provides the HTMLSearchMovieParser class (and the
search_movie_parser instance), used to parse the results of a search
for a given title.
E.g., for when searching for the title "the passion", the parsed
page would be:
    http://akas.imdb.com/find?q=the+passion&tt=on&mx=20

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
from imdb.utils import analyze_title, build_title
from utils import DOMParserBase, Attribute, Extractor, analyze_imdbid


class DOMBasicMovieParser(DOMParserBase):
    """Simply get the title of a movie and the imdbID.

    It's used by the DOMHTMLSearchMovieParser class to return a result
    for a direct match (when a search on IMDb results in a single
    movie, the web server sends directly the movie page."""
    # Stay generic enough to be used also for other DOMBasic*Parser classes.
    _titleAttrPath = ".//text()"
    _linkPath = "//link[@rel='canonical']"
    _titleFunct = lambda self, x: analyze_title(x or u'')

    def _init(self):
        self.preprocessors += [('<span class="tv-extra">TV mini-series</span>',
                                '<span class="tv-extra">(mini)</span>')]
        self.extractors = [Extractor(label='title',
                                path="//h1",
                                attrs=Attribute(key='title',
                                                path=self._titleAttrPath,
                                                postprocess=self._titleFunct)),
                            Extractor(label='link',
                                path=self._linkPath,
                                attrs=Attribute(key='link', path="./@href",
                                postprocess=lambda x: \
                                        analyze_imdbid((x or u'').replace(
                                            'http://pro.imdb.com', ''))
                                    ))]

    # Remove 'More at IMDb Pro' links.
    preprocessors = [(re.compile(r'<span class="pro-link".*?</span>'), ''),
            (re.compile(r'<a href="http://ad.doubleclick.net.*?;id=(co[0-9]{7});'), r'<a href="http://pro.imdb.com/company/\1"></a>< a href="')]

    def postprocess_data(self, data):
        if not 'link' in data:
            data = []
        else:
            link = data.pop('link')
            if (link and data):
                data = [(link, data)]
            else:
                data = []
        return data


def custom_analyze_title(title):
    """Remove garbage notes after the (year), (year/imdbIndex) or (year) (TV)"""
    # XXX: very crappy. :-(
    nt = title.split('    ')[0]
    if nt:
        title = nt
    if not title:
        return {}
    return analyze_title(title)

# Manage AKAs.
_reAKAStitles = re.compile(r'(?:aka) <em>"(.*?)(<br>|<\/td>)', re.I | re.M)

class DOMHTMLSearchMovieParser(DOMParserBase):
    """Parse the html page that the IMDb web server shows when the
    "new search system" is used, for movies."""

    _BaseParser = DOMBasicMovieParser
    _notDirectHitTitle = '<title>imdb title'
    _titleBuilder = lambda self, x: build_title(x)
    _linkPrefix = '/title/tt'

    _attrs = [Attribute(key='data',
                        multi=True,
                        path={
                            'link': "./a[1]/@href",
                            'info': ".//text()",
                            #'akas': ".//div[@class='_imdbpyAKA']//text()"
                            'akas': ".//p[@class='find-aka']//text()"
                            },
                        postprocess=lambda x: (
                            analyze_imdbid(x.get('link') or u''),
                            custom_analyze_title(x.get('info') or u''),
                            x.get('akas')
                        ))]
    extractors = [Extractor(label='search',
                        path="//td[3]/a[starts-with(@href, '/title/tt')]/..",
                        attrs=_attrs)]
    def _init(self):
        self.url = u''

    def _reset(self):
        self.url = u''

    def preprocess_string(self, html_string):
        if self._notDirectHitTitle in html_string[:1024].lower():
            if self._linkPrefix == '/title/tt':
                # Only for movies.
                html_string = html_string.replace('(TV mini-series)', '(mini)')
                html_string = html_string.replace('<p class="find-aka">',
                        '<p class="find-aka">::')
                #html_string = _reAKAStitles.sub(
                #        r'<div class="_imdbpyAKA">\1::</div>\2', html_string)
            return html_string
        # Direct hit!
        dbme = self._BaseParser(useModule=self._useModule)
        res = dbme.parse(html_string, url=self.url)
        if not res: return u''
        res = res['data']
        if not (res and res[0]): return u''
        link = '%s%s' % (self._linkPrefix, res[0][0])
        #    # Tries to cope with companies for which links to pro.imdb.com
        #    # are missing.
        #    link = self.url.replace(imdbURL_base[:-1], '')
        title = self._titleBuilder(res[0][1])
        if not (link and title): return u''
        link = link.replace('http://pro.imdb.com', '')
        new_html = '<td></td><td></td><td><a href="%s">%s</a></td>' % (link,
                                                                    title)
        return new_html

    def postprocess_data(self, data):
        if not data.has_key('data'):
            data['data'] = []
        results = getattr(self, 'results', None)
        if results is not None:
            data['data'][:] = data['data'][:results]
        # Horrible hack to support AKAs.
        if data and data['data'] and len(data['data'][0]) == 3 and \
                isinstance(data['data'][0], tuple):
            for idx, datum in enumerate(data['data']):
                if not isinstance(datum, tuple):
                    continue
                if datum[2] is not None:
                    akas = filter(None, datum[2].split('::'))
                    if self._linkPrefix == '/title/tt':
                        akas = [a.replace('" - ', '::').rstrip() for a in akas]
                        akas = [a.replace('aka "', '', 1).lstrip() for a in akas]
                    datum[1]['akas'] = akas
                    data['data'][idx] = (datum[0], datum[1])
                else:
                    data['data'][idx] = (datum[0], datum[1])
        return data

    def add_refs(self, data):
        return data


_OBJECTS = {
        'search_movie_parser': ((DOMHTMLSearchMovieParser,), None)
}

