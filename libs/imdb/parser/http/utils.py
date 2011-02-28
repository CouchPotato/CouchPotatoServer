"""
parser.http.utils module (imdb package).

This module provides miscellaneous utilities used by
the imdb.parser.http classes.

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
import logging

from imdb._exceptions import IMDbError

from imdb.utils import flatten, _Container
from imdb.Movie import Movie
from imdb.Person import Person
from imdb.Character import Character


# Year, imdbIndex and kind.
re_yearKind_index = re.compile(r'(\([0-9\?]{4}(?:/[IVXLCDM]+)?\)(?: \(mini\)| \(TV\)| \(V\)| \(VG\))?)')

# Match imdb ids in href tags
re_imdbid = re.compile(r'(title/tt|name/nm|character/ch|company/co)([0-9]+)')

def analyze_imdbid(href):
    """Return an imdbID from an URL."""
    if not href:
        return None
    match = re_imdbid.search(href)
    if not match:
        return None
    return str(match.group(2))


_modify_keys = list(Movie.keys_tomodify_list) + list(Person.keys_tomodify_list)
def _putRefs(d, re_titles, re_names, re_characters, lastKey=None):
    """Iterate over the strings inside list items or dictionary values,
    substitutes movie titles and person names with the (qv) references."""
    if isinstance(d, list):
        for i in xrange(len(d)):
            if isinstance(d[i], (unicode, str)):
                if lastKey in _modify_keys:
                    if re_names:
                        d[i] = re_names.sub(ur"'\1' (qv)", d[i])
                    if re_titles:
                        d[i] = re_titles.sub(ur'_\1_ (qv)', d[i])
                    if re_characters:
                        d[i] = re_characters.sub(ur'#\1# (qv)', d[i])
            elif isinstance(d[i], (list, dict)):
                _putRefs(d[i], re_titles, re_names, re_characters,
                        lastKey=lastKey)
    elif isinstance(d, dict):
        for k, v in d.items():
            lastKey = k
            if isinstance(v, (unicode, str)):
                if lastKey in _modify_keys:
                    if re_names:
                        d[k] = re_names.sub(ur"'\1' (qv)", v)
                    if re_titles:
                        d[k] = re_titles.sub(ur'_\1_ (qv)', v)
                    if re_characters:
                        d[k] = re_characters.sub(ur'#\1# (qv)', v)
            elif isinstance(v, (list, dict)):
                _putRefs(d[k], re_titles, re_names, re_characters,
                        lastKey=lastKey)


# Handle HTML/XML/SGML entities.
from htmlentitydefs import entitydefs
entitydefs = entitydefs.copy()
entitydefsget = entitydefs.get
entitydefs['nbsp'] = ' '

sgmlentity = {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"', 'apos': '\''}
sgmlentityget = sgmlentity.get
_sgmlentkeys = sgmlentity.keys()

entcharrefs = {}
entcharrefsget = entcharrefs.get
for _k, _v in entitydefs.items():
    if _k in _sgmlentkeys: continue
    if _v[0:2] == '&#':
        dec_code = _v[1:-1]
        _v = unichr(int(_v[2:-1]))
        entcharrefs[dec_code] = _v
    else:
        dec_code = '#' + str(ord(_v))
        _v = unicode(_v, 'latin_1', 'replace')
        entcharrefs[dec_code] = _v
    entcharrefs[_k] = _v
del _sgmlentkeys, _k, _v
entcharrefs['#160'] = u' '
entcharrefs['#xA0'] = u' '
entcharrefs['#xa0'] = u' '
entcharrefs['#XA0'] = u' '
entcharrefs['#x22'] = u'"'
entcharrefs['#X22'] = u'"'
# convert &x26; to &amp;, to make BeautifulSoup happy; beware that this
# leaves lone '&' in the html broken, but I assume this is better than
# the contrary...
entcharrefs['#38'] = u'&amp;'
entcharrefs['#x26'] = u'&amp;'
entcharrefs['#x26'] = u'&amp;'

re_entcharrefs = re.compile('&(%s|\#160|\#\d{1,5}|\#x[0-9a-f]{1,4});' %
                            '|'.join(map(re.escape, entcharrefs)), re.I)
re_entcharrefssub = re_entcharrefs.sub

sgmlentity.update(dict([('#34', u'"'), ('#38', u'&'),
                        ('#60', u'<'), ('#62', u'>'), ('#39', u"'")]))
re_sgmlref = re.compile('&(%s);' % '|'.join(map(re.escape, sgmlentity)))
re_sgmlrefsub = re_sgmlref.sub

# Matches XML-only single tags, like <br/> ; they are invalid in HTML,
# but widely used by IMDb web site. :-/
re_xmltags = re.compile('<([a-zA-Z]+)/>')


def _replXMLRef(match):
    """Replace the matched XML/HTML entities and references;
    replace everything except sgml entities like &lt;, &gt;, ..."""
    ref = match.group(1)
    value = entcharrefsget(ref)
    if value is None:
        if ref[0] == '#':
            ref_code = ref[1:]
            if ref_code in ('34', '38', '60', '62', '39'):
                return match.group(0)
            elif ref_code[0].lower() == 'x':
                #if ref[2:] == '26':
                #    # Don't convert &x26; to &amp;, to make BeautifulSoup happy.
                #    return '&amp;'
                return unichr(int(ref[2:], 16))
            else:
                return unichr(int(ref[1:]))
        else:
            return ref
    return value

def subXMLRefs(s):
    """Return the given html string with entity and char references
    replaced."""
    return re_entcharrefssub(_replXMLRef, s)

# XXX: no more used here; move it to mobile (they are imported by helpers, too)?
def _replSGMLRefs(match):
    """Replace the matched SGML entity."""
    ref = match.group(1)
    return sgmlentityget(ref, ref)

def subSGMLRefs(s):
    """Return the given html string with sgml entity and char references
    replaced."""
    return re_sgmlrefsub(_replSGMLRefs, s)


_b_p_logger = logging.getLogger('imdbpy.parser.http.build_person')
def build_person(txt, personID=None, billingPos=None,
                roleID=None, accessSystem='http', modFunct=None):
    """Return a Person instance from the tipical <tr>...</tr> strings
    found in the IMDb's web site."""
    #if personID is None
    #    _b_p_logger.debug('empty name or personID for "%s"', txt)
    notes = u''
    role = u''
    # Search the (optional) separator between name and role/notes.
    if txt.find('....') != -1:
        sep = '....'
    elif txt.find('...') != -1:
        sep = '...'
    else:
        sep = '...'
        # Replace the first parenthesis, assuming there are only
        # notes, after.
        # Rationale: no imdbIndex is (ever?) showed on the web site.
        txt = txt.replace('(', '...(', 1)
    txt_split = txt.split(sep, 1)
    name = txt_split[0].strip()
    if len(txt_split) == 2:
        role_comment = txt_split[1].strip()
        # Strip common endings.
        if role_comment[-4:] == ' and':
            role_comment = role_comment[:-4].rstrip()
        elif role_comment[-2:] == ' &':
            role_comment = role_comment[:-2].rstrip()
        elif role_comment[-6:] == '& ....':
            role_comment = role_comment[:-6].rstrip()
        # Get the notes.
        if roleID is not None:
            if not isinstance(roleID, list):
                cmt_idx = role_comment.find('(')
                if cmt_idx != -1:
                    role = role_comment[:cmt_idx].rstrip()
                    notes = role_comment[cmt_idx:]
                else:
                    # Just a role, without notes.
                    role = role_comment
            else:
                role = role_comment
        else:
            # We're managing something that doesn't have a 'role', so
            # everything are notes.
            notes = role_comment
    if role == '....': role = u''
    roleNotes = []
    # Manages multiple roleIDs.
    if isinstance(roleID, list):
        rolesplit = role.split('/')
        role = []
        for r in rolesplit:
            nidx = r.find('(')
            if nidx != -1:
                role.append(r[:nidx].rstrip())
                roleNotes.append(r[nidx:])
            else:
                role.append(r)
                roleNotes.append(None)
        lr = len(role)
        lrid = len(roleID)
        if lr > lrid:
            roleID += [None] * (lrid - lr)
        elif lr < lrid:
            roleID = roleID[:lr]
        for i, rid in enumerate(roleID):
            if rid is not None:
                roleID[i] = str(rid)
        if lr == 1:
            role = role[0]
            roleID = roleID[0]
    elif roleID is not None:
        roleID = str(roleID)
    if personID is not None:
        personID = str(personID)
    if (not name) or (personID is None):
        # Set to 'debug', since build_person is expected to receive some crap.
        _b_p_logger.debug('empty name or personID for "%s"', txt)
    # XXX: return None if something strange is detected?
    person = Person(name=name, personID=personID, currentRole=role,
                    roleID=roleID, notes=notes, billingPos=billingPos,
                    modFunct=modFunct, accessSystem=accessSystem)
    if roleNotes and len(roleNotes) == len(roleID):
        for idx, role in enumerate(person.currentRole):
            if roleNotes[idx]:
                role.notes = roleNotes[idx]
    return person


_b_m_logger = logging.getLogger('imdbpy.parser.http.build_movie')
# To shrink spaces.
re_spaces = re.compile(r'\s+')
def build_movie(txt, movieID=None, roleID=None, status=None,
                accessSystem='http', modFunct=None, _parsingCharacter=False,
                _parsingCompany=False):
    """Given a string as normally seen on the "categorized" page of
    a person on the IMDb's web site, returns a Movie instance."""
    if _parsingCharacter:
        _defSep = ' Played by '
    elif _parsingCompany:
        _defSep = ' ... '
    else:
        _defSep = ' .... '
    title = re_spaces.sub(' ', txt).strip()
    # Split the role/notes from the movie title.
    tsplit = title.split(_defSep, 1)
    role = u''
    notes = u''
    roleNotes = []
    if len(tsplit) == 2:
        title = tsplit[0].rstrip()
        role = tsplit[1].lstrip()
    if title[-9:] == 'TV Series':
        title = title[:-9].rstrip()
    elif title[-14:] == 'TV mini-series':
        title = title[:-14] + ' (mini)'
    # Try to understand where the movie title ends.
    while True:
        if title[-1:] != ')':
            # Ignore the silly "TV Series" notice.
            if title[-9:] == 'TV Series':
                title = title[:-9].rstrip()
                continue
            else:
                # Just a title: stop here.
                break
        # Try to match paired parentheses; yes: sometimes there are
        # parentheses inside comments...
        nidx = title.rfind('(')
        while (nidx != -1 and \
                    title[nidx:].count('(') != title[nidx:].count(')')):
            nidx = title[:nidx].rfind('(')
        # Unbalanced parentheses: stop here.
        if nidx == -1: break
        # The last item in parentheses seems to be a year: stop here.
        first4 = title[nidx+1:nidx+5]
        if (first4.isdigit() or first4 == '????') and \
                title[nidx+5:nidx+6] in (')', '/'): break
        # The last item in parentheses is a known kind: stop here.
        if title[nidx+1:-1] in ('TV', 'V', 'mini', 'VG'): break
        # Else, in parentheses there are some notes.
        # XXX: should the notes in the role half be kept separated
        #      from the notes in the movie title half?
        if notes: notes = '%s %s' % (title[nidx:], notes)
        else: notes = title[nidx:]
        title = title[:nidx].rstrip()
    if _parsingCharacter and roleID and not role:
        roleID = None
    if not roleID:
        roleID = None
    elif len(roleID) == 1:
        roleID = roleID[0]
    # Manages multiple roleIDs.
    if isinstance(roleID, list):
        tmprole = role.split('/')
        role = []
        for r in tmprole:
            nidx = r.find('(')
            if nidx != -1:
                role.append(r[:nidx].rstrip())
                roleNotes.append(r[nidx:])
            else:
                role.append(r)
                roleNotes.append(None)
        lr = len(role)
        lrid = len(roleID)
        if lr > lrid:
            roleID += [None] * (lrid - lr)
        elif lr < lrid:
            roleID = roleID[:lr]
        for i, rid in enumerate(roleID):
            if rid is not None:
                roleID[i] = str(rid)
        if lr == 1:
            role = role[0]
            roleID = roleID[0]
    elif roleID is not None:
        roleID = str(roleID)
    if movieID is not None:
        movieID = str(movieID)
    if (not title) or (movieID is None):
        _b_m_logger.error('empty title or movieID for "%s"', txt)
    m = Movie(title=title, movieID=movieID, notes=notes, currentRole=role,
                roleID=roleID, roleIsPerson=_parsingCharacter,
                modFunct=modFunct, accessSystem=accessSystem)
    if roleNotes and len(roleNotes) == len(roleID):
        for idx, role in enumerate(m.currentRole):
            if roleNotes[idx]:
                role.notes = roleNotes[idx]
    # Status can't be checked here, and must be detected by the parser.
    if status:
        m['status'] = status
    return m


class DOMParserBase(object):
    """Base parser to handle HTML data from the IMDb's web server."""
    _defGetRefs = False
    _containsObjects = False

    preprocessors = []
    extractors = []
    usingModule = None

    _logger = logging.getLogger('imdbpy.parser.http.domparser')

    def __init__(self, useModule=None):
        """Initialize the parser. useModule can be used to force it
        to use 'BeautifulSoup' or 'lxml'; by default, it's auto-detected,
        using 'lxml' if available and falling back to 'BeautifulSoup'
        otherwise."""
        # Module to use.
        if useModule is None:
            useModule = ('lxml', 'BeautifulSoup')
        if not isinstance(useModule, (tuple, list)):
            useModule = [useModule]
        self._useModule = useModule
        nrMods = len(useModule)
        _gotError = False
        for idx, mod in enumerate(useModule):
            mod = mod.strip().lower()
            try:
                if mod == 'lxml':
                    from lxml.html import fromstring
                    from lxml.etree import tostring
                    self._is_xml_unicode = False
                    self.usingModule = 'lxml'
                elif mod == 'beautifulsoup':
                    from bsouplxml.html import fromstring
                    from bsouplxml.etree import tostring
                    self._is_xml_unicode = True
                    self.usingModule = 'beautifulsoup'
                else:
                    self._logger.warn('unknown module "%s"' % mod)
                    continue
                self.fromstring = fromstring
                self._tostring = tostring
                if _gotError:
                    self._logger.warn('falling back to "%s"' % mod)
                break
            except ImportError, e:
                if idx+1 >= nrMods:
                    # Raise the exception, if we don't have any more
                    # options to try.
                    raise IMDbError, 'unable to use any parser in %s: %s' % \
                                    (str(useModule), str(e))
                else:
                    self._logger.warn('unable to use "%s": %s' % (mod, str(e)))
                    _gotError = True
                continue
        else:
            raise IMDbError, 'unable to use parsers in %s' % str(useModule)
        # Fall-back defaults.
        self._modFunct = None
        self._as = 'http'
        self._cname = self.__class__.__name__
        self._init()
        self.reset()

    def reset(self):
        """Reset the parser."""
        # Names and titles references.
        self._namesRefs = {}
        self._titlesRefs = {}
        self._charactersRefs = {}
        self._reset()

    def _init(self):
        """Subclasses can override this method, if needed."""
        pass

    def _reset(self):
        """Subclasses can override this method, if needed."""
        pass

    def parse(self, html_string, getRefs=None, **kwds):
        """Return the dictionary generated from the given html string;
        getRefs can be used to force the gathering of movies/persons/characters
        references."""
        self.reset()
        if getRefs is not None:
            self.getRefs = getRefs
        else:
            self.getRefs = self._defGetRefs
        # Useful only for the testsuite.
        if not isinstance(html_string, unicode):
            html_string = unicode(html_string, 'latin_1', 'replace')
        html_string = subXMLRefs(html_string)
        # Temporary fix: self.parse_dom must work even for empty strings.
        html_string = self.preprocess_string(html_string)
        html_string = html_string.strip()
        # tag attributes like title="&#x22;Family Guy&#x22;" will be
        # converted to title=""Family Guy"" and this confuses BeautifulSoup.
        if self.usingModule == 'beautifulsoup':
            html_string = html_string.replace('""', '"')
        if html_string:
            dom = self.get_dom(html_string)
            try:
                dom = self.preprocess_dom(dom)
            except Exception, e:
                self._logger.error('%s: caught exception preprocessing DOM',
                                    self._cname, exc_info=True)
            if self.getRefs:
                try:
                    self.gather_refs(dom)
                except Exception, e:
                    self._logger.warn('%s: unable to gather refs: %s',
                                    self._cname, exc_info=True)
            data = self.parse_dom(dom)
        else:
            data = {}
        try:
            data = self.postprocess_data(data)
        except Exception, e:
            self._logger.error('%s: caught exception postprocessing data',
                                self._cname, exc_info=True)
        if self._containsObjects:
            self.set_objects_params(data)
        data = self.add_refs(data)
        return data

    def _build_empty_dom(self):
        from bsouplxml import _bsoup
        return _bsoup.BeautifulSoup('')

    def get_dom(self, html_string):
        """Return a dom object, from the given string."""
        try:
            dom = self.fromstring(html_string)
            if dom is None:
                dom = self._build_empty_dom()
                self._logger.error('%s: using a fake empty DOM', self._cname)
            return dom
        except Exception, e:
            self._logger.error('%s: caught exception parsing DOM',
                                self._cname, exc_info=True)
            return self._build_empty_dom()

    def xpath(self, element, path):
        """Return elements matching the given XPath."""
        try:
            xpath_result = element.xpath(path)
            if self._is_xml_unicode:
                return xpath_result
            result = []
            for item in xpath_result:
                if isinstance(item, str):
                    item = unicode(item)
                result.append(item)
            return result
        except Exception, e:
            self._logger.error('%s: caught exception extracting XPath "%s"',
                                self._cname, path, exc_info=True)
            return []

    def tostring(self, element):
        """Convert the element to a string."""
        if isinstance(element, (unicode, str)):
            return unicode(element)
        else:
            try:
                return self._tostring(element, encoding=unicode)
            except Exception, e:
                self._logger.error('%s: unable to convert to string',
                                    self._cname, exc_info=True)
                return u''

    def clone(self, element):
        """Clone an element."""
        return self.fromstring(self.tostring(element))

    def preprocess_string(self, html_string):
        """Here we can modify the text, before it's parsed."""
        if not html_string:
            return html_string
        # Remove silly &nbsp;&raquo; chars.
        html_string = html_string.replace(u' \xbb', u'')
        try:
            preprocessors = self.preprocessors
        except AttributeError:
            return html_string
        for src, sub in preprocessors:
            # re._pattern_type is present only since Python 2.5.
            if callable(getattr(src, 'sub', None)):
                html_string = src.sub(sub, html_string)
            elif isinstance(src, str):
                html_string = html_string.replace(src, sub)
            elif callable(src):
                try:
                    html_string = src(html_string)
                except Exception, e:
                    _msg = '%s: caught exception preprocessing html'
                    self._logger.error(_msg, self._cname, exc_info=True)
                    continue
        ##print html_string.encode('utf8')
        return html_string

    def gather_refs(self, dom):
        """Collect references."""
        grParser = GatherRefs(useModule=self._useModule)
        grParser._as = self._as
        grParser._modFunct = self._modFunct
        refs = grParser.parse_dom(dom)
        refs = grParser.postprocess_data(refs)
        self._namesRefs = refs['names refs']
        self._titlesRefs = refs['titles refs']
        self._charactersRefs = refs['characters refs']

    def preprocess_dom(self, dom):
        """Last chance to modify the dom, before the rules in self.extractors
        are applied by the parse_dom method."""
        return dom

    def parse_dom(self, dom):
        """Parse the given dom according to the rules specified
        in self.extractors."""
        result = {}
        for extractor in self.extractors:
            ##print extractor.label
            if extractor.group is None:
                elements = [(extractor.label, element)
                            for element in self.xpath(dom, extractor.path)]
            else:
                groups = self.xpath(dom, extractor.group)
                elements = []
                for group in groups:
                    group_key = self.xpath(group, extractor.group_key)
                    if not group_key: continue
                    group_key = group_key[0]
                    # XXX: always tries the conversion to unicode:
                    #      BeautifulSoup.NavigableString is a subclass
                    #      of unicode, and so it's never converted.
                    group_key = self.tostring(group_key)
                    normalizer = extractor.group_key_normalize
                    if normalizer is not None:
                        if callable(normalizer):
                            try:
                                group_key = normalizer(group_key)
                            except Exception, e:
                                _m = '%s: unable to apply group_key normalizer'
                                self._logger.error(_m, self._cname,
                                                    exc_info=True)
                    group_elements = self.xpath(group, extractor.path)
                    elements.extend([(group_key, element)
                                     for element in group_elements])
            for group_key, element in elements:
                for attr in extractor.attrs:
                    if isinstance(attr.path, dict):
                        data = {}
                        for field in attr.path.keys():
                            path = attr.path[field]
                            value = self.xpath(element, path)
                            if not value:
                                data[field] = None
                            else:
                                # XXX: use u'' , to join?
                                data[field] = ''.join(value)
                    else:
                        data = self.xpath(element, attr.path)
                        if not data:
                            data = None
                        else:
                            data = attr.joiner.join(data)
                    if not data:
                        continue
                    attr_postprocess = attr.postprocess
                    if callable(attr_postprocess):
                        try:
                            data = attr_postprocess(data)
                        except Exception, e:
                            _m = '%s: unable to apply attr postprocess'
                            self._logger.error(_m, self._cname, exc_info=True)
                    key = attr.key
                    if key is None:
                        key = group_key
                    elif key.startswith('.'):
                        # assuming this is an xpath
                        try:
                            key = self.xpath(element, key)[0]
                        except IndexError:
                            self._logger.error('%s: XPath returned no items',
                                                self._cname, exc_info=True)
                    elif key.startswith('self.'):
                        key = getattr(self, key[5:])
                    if attr.multi:
                        if key not in result:
                            result[key] = []
                        result[key].append(data)
                    else:
                        if isinstance(data, dict):
                            result.update(data)
                        else:
                            result[key] = data
        return result

    def postprocess_data(self, data):
        """Here we can modify the data."""
        return data

    def set_objects_params(self, data):
        """Set parameters of Movie/Person/... instances, since they are
        not always set in the parser's code."""
        for obj in flatten(data, yieldDictKeys=True, scalar=_Container):
            obj.accessSystem = self._as
            obj.modFunct = self._modFunct

    def add_refs(self, data):
        """Modify data according to the expected output."""
        if self.getRefs:
            titl_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._titlesRefs.keys()])
            if titl_re != ur'()': re_titles = re.compile(titl_re, re.U)
            else: re_titles = None
            nam_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._namesRefs.keys()])
            if nam_re != ur'()': re_names = re.compile(nam_re, re.U)
            else: re_names = None
            chr_re = ur'(%s)' % '|'.join([re.escape(x) for x
                                            in self._charactersRefs.keys()])
            if chr_re != ur'()': re_characters = re.compile(chr_re, re.U)
            else: re_characters = None
            _putRefs(data, re_titles, re_names, re_characters)
        return {'data': data, 'titlesRefs': self._titlesRefs,
                'namesRefs': self._namesRefs,
                'charactersRefs': self._charactersRefs}


class Extractor(object):
    """Instruct the DOM parser about how to parse a document."""
    def __init__(self, label, path, attrs, group=None, group_key=None,
                 group_key_normalize=None):
        """Initialize an Extractor object, used to instruct the DOM parser
        about how to parse a document."""
        # rarely (never?) used, mostly for debugging purposes.
        self.label = label
        self.group = group
        if group_key is None:
            self.group_key = ".//text()"
        else:
            self.group_key = group_key
        self.group_key_normalize = group_key_normalize
        self.path = path
        # A list of attributes to fetch.
        if isinstance(attrs, Attribute):
            attrs = [attrs]
        self.attrs = attrs

    def __repr__(self):
        """String representation of an Extractor object."""
        r = '<Extractor id:%s (label=%s, path=%s, attrs=%s, group=%s, ' \
                'group_key=%s group_key_normalize=%s)>' % (id(self),
                        self.label, self.path, repr(self.attrs), self.group,
                        self.group_key, self.group_key_normalize)
        return r


class Attribute(object):
    """The attribute to consider, for a given node."""
    def __init__(self, key, multi=False, path=None, joiner=None,
                 postprocess=None):
        """Initialize an Attribute object, used to specify the
        attribute to consider, for a given node."""
        # The key under which information will be saved; can be a string or an
        # XPath. If None, the label of the containing extractor will be used.
        self.key = key
        self.multi = multi
        self.path = path
        if joiner is None:
            joiner = ''
        self.joiner = joiner
        # Post-process this set of information.
        self.postprocess = postprocess

    def __repr__(self):
        """String representation of an Attribute object."""
        r = '<Attribute id:%s (key=%s, multi=%s, path=%s, joiner=%s, ' \
                'postprocess=%s)>' % (id(self), self.key,
                        self.multi, repr(self.path),
                        self.joiner, repr(self.postprocess))
        return r


def _parse_ref(text, link, info):
    """Manage links to references."""
    if link.find('/title/tt') != -1:
        yearK = re_yearKind_index.match(info)
        if yearK and yearK.start() == 0:
            text += ' %s' % info[:yearK.end()]
    return (text.replace('\n', ' '), link)


class GatherRefs(DOMParserBase):
    """Parser used to gather references to movies, persons and characters."""
    _attrs = [Attribute(key=None, multi=True,
                        path={
                            'text': './text()',
                            'link': './@href',
                            'info': './following::text()[1]'
                            },
        postprocess=lambda x: _parse_ref(x.get('text'), x.get('link'),
                                         (x.get('info') or u'').strip()))]
    extractors = [
        Extractor(label='names refs',
            path="//a[starts-with(@href, '/name/nm')][string-length(@href)=16]",
            attrs=_attrs),

        Extractor(label='titles refs',
            path="//a[starts-with(@href, '/title/tt')]" \
                    "[string-length(@href)=17]",
            attrs=_attrs),

        Extractor(label='characters refs',
            path="//a[starts-with(@href, '/character/ch')]" \
                    "[string-length(@href)=21]",
            attrs=_attrs),
            ]

    def postprocess_data(self, data):
        result = {}
        for item in ('names refs', 'titles refs', 'characters refs'):
            result[item] = {}
            for k, v in data.get(item, []):
                if not v.endswith('/'): continue
                imdbID = analyze_imdbid(v)
                if item == 'names refs':
                    obj = Person(personID=imdbID, name=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                elif item == 'titles refs':
                    obj = Movie(movieID=imdbID, title=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                else:
                    obj = Character(characterID=imdbID, name=k,
                                accessSystem=self._as, modFunct=self._modFunct)
                # XXX: companies aren't handled: are they ever found in text,
                #      as links to their page?
                result[item][k] = obj
        return result

    def add_refs(self, data):
        return data


