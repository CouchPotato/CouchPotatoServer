"""
parser.sql package (imdb package).

This package provides the IMDbSqlAccessSystem class used to access
IMDb's data through a SQL database.  Every database supported by
the SQLObject _AND_ SQLAlchemy Object Relational Managers is available.
the imdb.IMDb function will return an instance of this class when
called with the 'accessSystem' argument set to "sql", "database" or "db".

Copyright 2005-2010 Davide Alberani <da@erlug.linux.it>

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

# FIXME: this whole module was written in a veeery short amount of time.
#        The code should be commented, rewritten and cleaned. :-)

import re
import logging
from difflib import SequenceMatcher
from codecs import lookup

from imdb import IMDbBase
from imdb.utils import normalizeName, normalizeTitle, build_title, \
                        build_name, analyze_name, analyze_title, \
                        canonicalTitle, canonicalName, re_titleRef, \
                        build_company_name, re_episodes, _unicodeArticles, \
                        analyze_company_name, re_year_index, re_nameRef
from imdb.Person import Person
from imdb.Movie import Movie
from imdb.Company import Company
from imdb._exceptions import IMDbDataAccessError, IMDbError


# Logger for miscellaneous functions.
_aux_logger = logging.getLogger('imdbpy.parser.sql.aux')

# =============================
# Things that once upon a time were in imdb.parser.common.locsql.

def titleVariations(title, fromPtdf=0):
    """Build title variations useful for searches; if fromPtdf is true,
    the input is assumed to be in the plain text data files format."""
    if fromPtdf: title1 = u''
    else: title1 = title
    title2 = title3 = u''
    if fromPtdf or re_year_index.search(title):
        # If it appears to have a (year[/imdbIndex]) indication,
        # assume that a long imdb canonical name was provided.
        titldict = analyze_title(title, canonical=1)
        # title1: the canonical name.
        title1 = titldict['title']
        if titldict['kind'] != 'episode':
            # title3: the long imdb canonical name.
            if fromPtdf: title3 = title
            else: title3 = build_title(titldict, canonical=1, ptdf=1)
        else:
            title1 = normalizeTitle(title1)
            title3 = build_title(titldict, canonical=1, ptdf=1)
    else:
        # Just a title.
        # title1: the canonical title.
        title1 = canonicalTitle(title)
        title3 = u''
    # title2 is title1 without the article, or title1 unchanged.
    if title1:
        title2 = title1
        t2s = title2.split(u', ')
        if t2s[-1].lower() in _unicodeArticles:
            title2 = u', '.join(t2s[:-1])
    _aux_logger.debug('title variations: 1:[%s] 2:[%s] 3:[%s]',
                        title1, title2, title3)
    return title1, title2, title3


re_nameIndex = re.compile(r'\(([IVXLCDM]+)\)')

def nameVariations(name, fromPtdf=0):
    """Build name variations useful for searches; if fromPtdf is true,
    the input is assumed to be in the plain text data files format."""
    name1 = name2 = name3 = u''
    if fromPtdf or re_nameIndex.search(name):
        # We've a name with an (imdbIndex)
        namedict = analyze_name(name, canonical=1)
        # name1 is the name in the canonical format.
        name1 = namedict['name']
        # name3 is the canonical name with the imdbIndex.
        if fromPtdf:
            if namedict.has_key('imdbIndex'):
                name3 = name
        else:
            name3 = build_name(namedict, canonical=1)
    else:
        # name1 is the name in the canonical format.
        name1 = canonicalName(name)
        name3 = u''
    # name2 is the name in the normal format, if it differs from name1.
    name2 = normalizeName(name1)
    if name1 == name2: name2 = u''
    _aux_logger.debug('name variations: 1:[%s] 2:[%s] 3:[%s]',
                        name1, name2, name3)
    return name1, name2, name3


try:
    from cutils import ratcliff as _ratcliff
    def ratcliff(s1, s2, sm):
        """Return the Ratcliff-Obershelp value between the two strings,
        using the C implementation."""
        return _ratcliff(s1.encode('latin_1', 'replace'),
                        s2.encode('latin_1', 'replace'))
except ImportError:
    _aux_logger.warn('Unable to import the cutils.ratcliff function.'
                    '  Searching names and titles using the "sql"'
                    ' data access system will be slower.')

    def ratcliff(s1, s2, sm):
        """Ratcliff-Obershelp similarity."""
        STRING_MAXLENDIFFER = 0.7
        s1len = len(s1)
        s2len = len(s2)
        if s1len < s2len:
            threshold = float(s1len) / s2len
        else:
            threshold = float(s2len) / s1len
        if threshold < STRING_MAXLENDIFFER:
            return 0.0
        sm.set_seq2(s2.lower())
        return sm.ratio()


def merge_roles(mop):
    """Merge multiple roles."""
    new_list = []
    for m in mop:
        if m in new_list:
            keep_this = new_list[new_list.index(m)]
            if not isinstance(keep_this.currentRole, list):
                keep_this.currentRole = [keep_this.currentRole]
            keep_this.currentRole.append(m.currentRole)
        else:
            new_list.append(m)
    return new_list


def scan_names(name_list, name1, name2, name3, results=0, ro_thresold=None,
                _scan_character=False):
    """Scan a list of names, searching for best matches against
    the given variations."""
    if ro_thresold is not None: RO_THRESHOLD = ro_thresold
    else: RO_THRESHOLD = 0.6
    sm1 = SequenceMatcher()
    sm2 = SequenceMatcher()
    sm3 = SequenceMatcher()
    sm1.set_seq1(name1.lower())
    if name2: sm2.set_seq1(name2.lower())
    if name3: sm3.set_seq1(name3.lower())
    resd = {}
    for i, n_data in name_list:
        nil = n_data['name']
        # XXX: on Symbian, here we get a str; not sure this is the
        #      right place to fix it.
        if isinstance(nil, str):
            nil = unicode(nil, 'latin1', 'ignore')
        # Distance with the canonical name.
        ratios = [ratcliff(name1, nil, sm1) + 0.05]
        namesurname = u''
        if not _scan_character:
            nils = nil.split(', ', 1)
            surname = nils[0]
            if len(nils) == 2: namesurname = '%s %s' % (nils[1], surname)
        else:
            nils = nil.split(' ', 1)
            surname = nils[-1]
            namesurname = nil
        if surname != nil:
            # Distance with the "Surname" in the database.
            ratios.append(ratcliff(name1, surname, sm1))
            if not _scan_character:
                ratios.append(ratcliff(name1, namesurname, sm1))
            if name2:
                ratios.append(ratcliff(name2, surname, sm2))
                # Distance with the "Name Surname" in the database.
                if namesurname:
                    ratios.append(ratcliff(name2, namesurname, sm2))
        if name3:
            # Distance with the long imdb canonical name.
            ratios.append(ratcliff(name3,
                        build_name(n_data, canonical=1), sm3) + 0.1)
        ratio = max(ratios)
        if ratio >= RO_THRESHOLD:
            if resd.has_key(i):
                if ratio > resd[i][0]: resd[i] = (ratio, (i, n_data))
            else: resd[i] = (ratio, (i, n_data))
    res = resd.values()
    res.sort()
    res.reverse()
    if results > 0: res[:] = res[:results]
    return res


def scan_titles(titles_list, title1, title2, title3, results=0,
                searchingEpisode=0, onlyEpisodes=0, ro_thresold=None):
    """Scan a list of titles, searching for best matches against
    the given variations."""
    if ro_thresold is not None: RO_THRESHOLD = ro_thresold
    else: RO_THRESHOLD = 0.6
    sm1 = SequenceMatcher()
    sm2 = SequenceMatcher()
    sm3 = SequenceMatcher()
    sm1.set_seq1(title1.lower())
    sm2.set_seq2(title2.lower())
    if title3:
        sm3.set_seq1(title3.lower())
        if title3[-1] == '}': searchingEpisode = 1
    hasArt = 0
    if title2 != title1: hasArt = 1
    resd = {}
    for i, t_data in titles_list:
        if onlyEpisodes:
            if t_data.get('kind') != 'episode':
                continue
            til = t_data['title']
            if til[-1] == ')':
                dateIdx = til.rfind('(')
                if dateIdx != -1:
                    til = til[:dateIdx].rstrip()
            if not til:
                continue
            ratio = ratcliff(title1, til, sm1)
            if ratio >= RO_THRESHOLD:
                resd[i] = (ratio, (i, t_data))
            continue
        if searchingEpisode:
            if t_data.get('kind') != 'episode': continue
        elif t_data.get('kind') == 'episode': continue
        til = t_data['title']
        # XXX: on Symbian, here we get a str; not sure this is the
        #      right place to fix it.
        if isinstance(til, str):
            til = unicode(til, 'latin1', 'ignore')
        # Distance with the canonical title (with or without article).
        #   titleS      -> titleR
        #   titleS, the -> titleR, the
        if not searchingEpisode:
            til = canonicalTitle(til)
            ratios = [ratcliff(title1, til, sm1) + 0.05]
            # til2 is til without the article, if present.
            til2 = til
            tils = til2.split(', ')
            matchHasArt = 0
            if tils[-1].lower() in _unicodeArticles:
                til2 = ', '.join(tils[:-1])
                matchHasArt = 1
            if hasArt and not matchHasArt:
                #   titleS[, the]  -> titleR
                ratios.append(ratcliff(title2, til, sm2))
            elif matchHasArt and not hasArt:
                #   titleS  -> titleR[, the]
                ratios.append(ratcliff(title1, til2, sm1))
        else:
            ratios = [0.0]
        if title3:
            # Distance with the long imdb canonical title.
            ratios.append(ratcliff(title3,
                        build_title(t_data, canonical=1, ptdf=1), sm3) + 0.1)
        ratio = max(ratios)
        if ratio >= RO_THRESHOLD:
            if resd.has_key(i):
                if ratio > resd[i][0]:
                    resd[i] = (ratio, (i, t_data))
            else: resd[i] = (ratio, (i, t_data))
    res = resd.values()
    res.sort()
    res.reverse()
    if results > 0: res[:] = res[:results]
    return res


def scan_company_names(name_list, name1, results=0, ro_thresold=None):
    """Scan a list of company names, searching for best matches against
    the given name.  Notice that this function takes a list of
    strings, and not a list of dictionaries."""
    if ro_thresold is not None: RO_THRESHOLD = ro_thresold
    else: RO_THRESHOLD = 0.6
    sm1 = SequenceMatcher()
    sm1.set_seq1(name1.lower())
    resd = {}
    withoutCountry = not name1.endswith(']')
    for i, n in name_list:
        # XXX: on Symbian, here we get a str; not sure this is the
        #      right place to fix it.
        if isinstance(n, str):
            n = unicode(n, 'latin1', 'ignore')
        o_name = n
        var = 0.0
        if withoutCountry and n.endswith(']'):
            cidx = n.rfind('[')
            if cidx != -1:
                n = n[:cidx].rstrip()
                var = -0.05
        # Distance with the company name.
        ratio = ratcliff(name1, n, sm1) + var
        if ratio >= RO_THRESHOLD:
            if resd.has_key(i):
                if ratio > resd[i][0]: resd[i] = (ratio,
                                            (i, analyze_company_name(o_name)))
            else:
                resd[i] = (ratio, (i, analyze_company_name(o_name)))
    res = resd.values()
    res.sort()
    res.reverse()
    if results > 0: res[:] = res[:results]
    return res


try:
    from cutils import soundex
except ImportError:
    _aux_logger.warn('Unable to import the cutils.soundex function.'
                    '  Searches of movie titles and person names will be'
                    ' a bit slower.')

    _translate = dict(B='1', C='2', D='3', F='1', G='2', J='2', K='2', L='4',
                      M='5', N='5', P='1', Q='2', R='6', S='2', T='3', V='1',
                      X='2', Z='2')
    _translateget = _translate.get
    _re_non_ascii = re.compile(r'^[^a-z]*', re.I)
    SOUNDEX_LEN = 5

    def soundex(s):
        """Return the soundex code for the given string."""
        # Maximum length of the soundex code.
        s = _re_non_ascii.sub('', s)
        if not s: return None
        s = s.upper()
        soundCode =  s[0]
        for c in s[1:]:
            cw = _translateget(c, '0')
            if cw != '0' and soundCode[-1] != cw:
                soundCode += cw
        return soundCode[:SOUNDEX_LEN] or None


def _sortKeywords(keyword, kwds):
    """Sort a list of keywords, based on the searched one."""
    sm = SequenceMatcher()
    sm.set_seq1(keyword.lower())
    ratios = [(ratcliff(keyword, k, sm), k) for k in kwds]
    checkContained = False
    if len(keyword) > 4:
        checkContained = True
    for idx, data in enumerate(ratios):
        ratio, key = data
        if key.startswith(keyword):
            ratios[idx] = (ratio+0.5, key)
        elif checkContained and keyword in key:
            ratios[idx] = (ratio+0.3, key)
    ratios.sort()
    ratios.reverse()
    return [r[1] for r in ratios]


def filterSimilarKeywords(keyword, kwdsIterator):
    """Return a sorted list of keywords similar to the one given."""
    seenDict = {}
    kwdSndx = soundex(keyword.encode('ascii', 'ignore'))
    matches = []
    matchesappend = matches.append
    checkContained = False
    if len(keyword) > 4:
        checkContained = True
    for movieID, key in kwdsIterator:
        if key in seenDict:
            continue
        seenDict[key] = None
        if checkContained and keyword in key:
            matchesappend(key)
            continue
        if kwdSndx == soundex(key.encode('ascii', 'ignore')):
            matchesappend(key)
    return _sortKeywords(keyword, matches)



# =============================

_litlist = ['screenplay/teleplay', 'novel', 'adaption', 'book',
            'production process protocol', 'interviews',
            'printed media reviews', 'essays', 'other literature']
_litd = dict([(x, ('literature', x)) for x in _litlist])

_buslist = ['budget', 'weekend gross', 'gross', 'opening weekend', 'rentals',
            'admissions', 'filming dates', 'production dates', 'studios',
            'copyright holder']
_busd = dict([(x, ('business', x)) for x in _buslist])


def _reGroupDict(d, newgr):
    """Regroup keys in the d dictionary in subdictionaries, based on
    the scheme in the newgr dictionary.
    E.g.: in the newgr, an entry 'LD label': ('laserdisc', 'label')
    tells the _reGroupDict() function to take the entry with
    label 'LD label' (as received from the sql database)
    and put it in the subsection (another dictionary) named
    'laserdisc', using the key 'label'."""
    r = {}
    newgrks = newgr.keys()
    for k, v in d.items():
        if k in newgrks:
            r.setdefault(newgr[k][0], {})[newgr[k][1]] = v
            # A not-so-clearer version:
            ##r.setdefault(newgr[k][0], {})
            ##r[newgr[k][0]][newgr[k][1]] = v
        else: r[k] = v
    return r


def _groupListBy(l, index):
    """Regroup items in a list in a list of lists, grouped by
    the value at the given index."""
    tmpd = {}
    for item in l:
        tmpd.setdefault(item[index], []).append(item)
    res = tmpd.values()
    return res


def sub_dict(d, keys):
    """Return the subdictionary of 'd', with just the keys listed in 'keys'."""
    return dict([(k, d[k]) for k in keys if k in d])


def get_movie_data(movieID, kindDict, fromAka=0, _table=None):
    """Return a dictionary containing data about the given movieID;
    if fromAka is true, the AkaTitle table is searched; _table is
    reserved for the imdbpy2sql.py script."""
    if _table is not None:
        Table = _table
    else:
        if not fromAka: Table = Title
        else: Table = AkaTitle
    m = Table.get(movieID)
    mdict = {'title': m.title, 'kind': kindDict[m.kindID],
            'year': m.productionYear, 'imdbIndex': m.imdbIndex,
            'season': m.seasonNr, 'episode': m.episodeNr}
    if not fromAka:
        if m.seriesYears is not None:
            mdict['series years'] = unicode(m.seriesYears)
    if mdict['imdbIndex'] is None: del mdict['imdbIndex']
    if mdict['year'] is None: del mdict['year']
    else:
        try:
            mdict['year'] = int(mdict['year'])
        except (TypeError, ValueError):
            del mdict['year']
    if mdict['season'] is None: del mdict['season']
    else:
        try: mdict['season'] = int(mdict['season'])
        except: pass
    if mdict['episode'] is None: del mdict['episode']
    else:
        try: mdict['episode'] = int(mdict['episode'])
        except: pass
    episodeOfID = m.episodeOfID
    if episodeOfID is not None:
        ser_dict = get_movie_data(episodeOfID, kindDict, fromAka)
        mdict['episode of'] = Movie(data=ser_dict, movieID=episodeOfID,
                                    accessSystem='sql')
        if fromAka:
            ser_note = AkaTitle.get(episodeOfID).note
            if ser_note:
                mdict['episode of'].notes = ser_note
    return mdict


def _iterKeywords(results):
    """Iterate over (key.id, key.keyword) columns of a selection of
    the Keyword table."""
    for key in results:
        yield key.id, key.keyword


def getSingleInfo(table, movieID, infoType, notAList=False):
    """Return a dictionary in the form {infoType: infoListOrString},
    retrieving a single set of information about a given movie, from
    the specified table."""
    infoTypeID = InfoType.select(InfoType.q.info == infoType)
    if infoTypeID.count() == 0:
        return {}
    res = table.select(AND(table.q.movieID == movieID,
                        table.q.infoTypeID == infoTypeID[0].id))
    retList = []
    for r in res:
        info = r.info
        note = r.note
        if note:
            info += u'::%s' % note
        retList.append(info)
    if not retList:
        return {}
    if not notAList: return {infoType: retList}
    else: return {infoType: retList[0]}


def _cmpTop(a, b, what='top 250 rank'):
    """Compare function used to sort top 250/bottom 10 rank."""
    av = int(a[1].get(what))
    bv = int(b[1].get(what))
    if av == bv:
        return 0
    return (-1, 1)[av > bv]

def _cmpBottom(a, b):
    """Compare function used to sort top 250/bottom 10 rank."""
    return _cmpTop(a, b, what='bottom 10 rank')


class IMDbSqlAccessSystem(IMDbBase):
    """The class used to access IMDb's data through a SQL database."""

    accessSystem = 'sql'
    _sql_logger = logging.getLogger('imdbpy.parser.sql')

    def __init__(self, uri, adultSearch=1, useORM=None, *arguments, **keywords):
        """Initialize the access system."""
        IMDbBase.__init__(self, *arguments, **keywords)
        if useORM is None:
            useORM = ('sqlobject', 'sqlalchemy')
        if not isinstance(useORM, (tuple, list)):
            if ',' in useORM:
                useORM = useORM.split(',')
            else:
                useORM = [useORM]
        self.useORM = useORM
        nrMods = len(useORM)
        _gotError = False
        DB_TABLES = []
        for idx, mod in enumerate(useORM):
            mod = mod.strip().lower()
            try:
                if mod == 'sqlalchemy':
                    from alchemyadapter import getDBTables, NotFoundError, \
                                                setConnection, AND, OR, IN, \
                                                ISNULL, CONTAINSSTRING, toUTF8
                elif mod == 'sqlobject':
                    from objectadapter import getDBTables, NotFoundError, \
                                                setConnection, AND, OR, IN, \
                                                ISNULL, CONTAINSSTRING, toUTF8
                else:
                    self._sql_logger.warn('unknown module "%s"' % mod)
                    continue
                self._sql_logger.info('using %s ORM', mod)
                # XXX: look ma'... black magic!  It's used to make
                #      TableClasses and some functions accessible
                #      through the whole module.
                for k, v in [('NotFoundError', NotFoundError),
                            ('AND', AND), ('OR', OR), ('IN', IN),
                            ('ISNULL', ISNULL),
                            ('CONTAINSSTRING', CONTAINSSTRING)]:
                    globals()[k] = v
                self.toUTF8 = toUTF8
                DB_TABLES = getDBTables(uri)
                for t in DB_TABLES:
                    globals()[t._imdbpyName] = t
                if _gotError:
                    self._sql_logger.warn('falling back to "%s"' % mod)
                break
            except ImportError, e:
                if idx+1 >= nrMods:
                    raise IMDbError, 'unable to use any ORM in %s: %s' % (
                                                    str(useORM), str(e))
                else:
                    self._sql_logger.warn('unable to use "%s": %s' % (mod,
                                                                    str(e)))
                    _gotError = True
                continue
        else:
            raise IMDbError, 'unable to use any ORM in %s' % str(useORM)
        # Set the connection to the database.
        self._sql_logger.debug('connecting to %s', uri)
        try:
            self._connection = setConnection(uri, DB_TABLES)
        except AssertionError, e:
            raise IMDbDataAccessError, \
                    'unable to connect to the database server; ' + \
                    'complete message: "%s"' % str(e)
        self.Error = self._connection.module.Error
        # Maps some IDs to the corresponding strings.
        self._kind = {}
        self._kindRev = {}
        self._sql_logger.debug('reading constants from the database')
        try:
            for kt in KindType.select():
                self._kind[kt.id] = kt.kind
                self._kindRev[str(kt.kind)] = kt.id
        except self.Error:
            # NOTE: you can also get the error, but - at least with
            #       MySQL - it also contains the password, and I don't
            #       like the idea to print it out.
            raise IMDbDataAccessError, \
                    'unable to connect to the database server'
        self._role = {}
        for rl in RoleType.select():
            self._role[rl.id] = str(rl.role)
        self._info = {}
        self._infoRev = {}
        for inf in InfoType.select():
            self._info[inf.id] = str(inf.info)
            self._infoRev[str(inf.info)] = inf.id
        self._compType = {}
        for cType in CompanyType.select():
            self._compType[cType.id] = cType.kind
        info = [(it.id, it.info) for it in InfoType.select()]
        self._compcast = {}
        for cc in CompCastType.select():
            self._compcast[cc.id] = str(cc.kind)
        self._link = {}
        for lt in LinkType.select():
            self._link[lt.id] = str(lt.link)
        self._moviesubs = {}
        # Build self._moviesubs, a dictionary used to rearrange
        # the data structure for a movie object.
        for vid, vinfo in info:
            if not vinfo.startswith('LD '): continue
            self._moviesubs[vinfo] = ('laserdisc', vinfo[3:])
        self._moviesubs.update(_litd)
        self._moviesubs.update(_busd)
        self.do_adult_search(adultSearch)

    def _findRefs(self, o, trefs, nrefs):
        """Find titles or names references in strings."""
        if isinstance(o, (unicode, str)):
            for title in re_titleRef.findall(o):
                a_title = analyze_title(title, canonical=0)
                rtitle = build_title(a_title, ptdf=1)
                if trefs.has_key(rtitle): continue
                movieID = self._getTitleID(rtitle)
                if movieID is None:
                    movieID = self._getTitleID(title)
                if movieID is None:
                    continue
                m = Movie(title=rtitle, movieID=movieID,
                            accessSystem=self.accessSystem)
                trefs[rtitle] = m
                rtitle2 = canonicalTitle(a_title.get('title', u''))
                if rtitle2 and rtitle2 != rtitle and rtitle2 != title:
                    trefs[rtitle2] = m
                if title != rtitle:
                    trefs[title] = m
            for name in re_nameRef.findall(o):
                a_name = analyze_name(name, canonical=1)
                rname = build_name(a_name, canonical=1)
                if nrefs.has_key(rname): continue
                personID = self._getNameID(rname)
                if personID is None:
                    personID = self._getNameID(name)
                if personID is None: continue
                p = Person(name=rname, personID=personID,
                            accessSystem=self.accessSystem)
                nrefs[rname] = p
                rname2 = normalizeName(a_name.get('name', u''))
                if rname2 and rname2 != rname:
                    nrefs[rname2] = p
                if name != rname and name != rname2:
                    nrefs[name] = p
        elif isinstance(o, (list, tuple)):
            for item in o:
                self._findRefs(item, trefs, nrefs)
        elif isinstance(o, dict):
            for value in o.values():
                self._findRefs(value, trefs, nrefs)
        return (trefs, nrefs)

    def _extractRefs(self, o):
        """Scan for titles or names references in strings."""
        trefs = {}
        nrefs = {}
        try:
            return self._findRefs(o, trefs, nrefs)
        except RuntimeError, e:
            # Symbian/python 2.2 has a poor regexp implementation.
            import warnings
            warnings.warn('RuntimeError in '
                    "imdb.parser.sql.IMDbSqlAccessSystem; "
                    "if it's not a recursion limit exceeded and we're not "
                    "running in a Symbian environment, it's a bug:\n%s" % e)
            return (trefs, nrefs)

    def _changeAKAencoding(self, akanotes, akatitle):
        """Return akatitle in the correct charset, as specified in
        the akanotes field; if akatitle doesn't need to be modified,
        return None."""
        oti = akanotes.find('(original ')
        if oti == -1: return None
        ote = akanotes[oti+10:].find(' title)')
        if ote != -1:
            cs_info = akanotes[oti+10:oti+10+ote].lower().split()
            for e in cs_info:
                # excludes some strings that clearly are not encoding.
                if e in ('script', '', 'cyrillic', 'greek'): continue
                if e.startswith('iso-') and e.find('latin') != -1:
                    e = e[4:].replace('-', '')
                try:
                    lookup(e)
                    lat1 = akatitle.encode('latin_1', 'replace')
                    return unicode(lat1, e, 'replace')
                except (LookupError, ValueError, TypeError):
                    continue
        return None

    def _buildNULLCondition(self, col, val):
        """Build a comparison for columns where values can be NULL."""
        if val is None:
            return ISNULL(col)
        else:
            if isinstance(val, (int, long)):
                return col == val
            else:
                return col == self.toUTF8(val)

    def _getTitleID(self, title):
        """Given a long imdb canonical title, returns a movieID or
        None if not found."""
        td = analyze_title(title)
        condition = None
        if td['kind'] == 'episode':
            epof = td['episode of']
            seriesID = [s.id for s in Title.select(
                        AND(Title.q.title == self.toUTF8(epof['title']),
                            self._buildNULLCondition(Title.q.imdbIndex,
                                                    epof.get('imdbIndex')),
                           Title.q.kindID == self._kindRev[epof['kind']],
                           self._buildNULLCondition(Title.q.productionYear,
                                                    epof.get('year'))))]
            if seriesID:
                condition = AND(IN(Title.q.episodeOfID, seriesID),
                                Title.q.title == self.toUTF8(td['title']),
                                self._buildNULLCondition(Title.q.imdbIndex,
                                                        td.get('imdbIndex')),
                                Title.q.kindID == self._kindRev[td['kind']],
                                self._buildNULLCondition(Title.q.productionYear,
                                                        td.get('year')))
        if condition is None:
            condition = AND(Title.q.title == self.toUTF8(td['title']),
                            self._buildNULLCondition(Title.q.imdbIndex,
                                                    td.get('imdbIndex')),
                            Title.q.kindID == self._kindRev[td['kind']],
                            self._buildNULLCondition(Title.q.productionYear,
                                                    td.get('year')))
        res = Title.select(condition)
        try:
            if res.count() != 1:
                return None
        except (UnicodeDecodeError, TypeError):
            return None
        return res[0].id

    def _getNameID(self, name):
        """Given a long imdb canonical name, returns a personID or
        None if not found."""
        nd = analyze_name(name)
        res = Name.select(AND(Name.q.name == self.toUTF8(nd['name']),
                                self._buildNULLCondition(Name.q.imdbIndex,
                                                        nd.get('imdbIndex'))))
        try:
            c = res.count()
            if res.count() != 1:
                return None
        except (UnicodeDecodeError, TypeError):
            return None
        return res[0].id

    def _normalize_movieID(self, movieID):
        """Normalize the given movieID."""
        try:
            return int(movieID)
        except (ValueError, OverflowError):
            raise IMDbError, 'movieID "%s" can\'t be converted to integer' % \
                            movieID

    def _normalize_personID(self, personID):
        """Normalize the given personID."""
        try:
            return int(personID)
        except (ValueError, OverflowError):
            raise IMDbError, 'personID "%s" can\'t be converted to integer' % \
                            personID

    def _normalize_characterID(self, characterID):
        """Normalize the given characterID."""
        try:
            return int(characterID)
        except (ValueError, OverflowError):
            raise IMDbError, 'characterID "%s" can\'t be converted to integer' \
                            % characterID

    def _normalize_companyID(self, companyID):
        """Normalize the given companyID."""
        try:
            return int(companyID)
        except (ValueError, OverflowError):
            raise IMDbError, 'companyID "%s" can\'t be converted to integer' \
                            % companyID

    def get_imdbMovieID(self, movieID):
        """Translate a movieID in an imdbID.
        If not in the database, try an Exact Primary Title search on IMDb;
        return None if it's unable to get the imdbID.
        """
        try: movie = Title.get(movieID)
        except NotFoundError: return None
        imdbID = movie.imdbID
        if imdbID is not None: return '%07d' % imdbID
        m_dict = get_movie_data(movie.id, self._kind)
        titline = build_title(m_dict, ptdf=1)
        imdbID = self.title2imdbID(titline)
        # If the imdbID was retrieved from the web and was not in the
        # database, update the database (ignoring errors, because it's
        # possibile that the current user has not update privileges).
        # There're times when I think I'm a genius; this one of
        # those times... <g>
        if imdbID is not None:
            try: movie.imdbID = int(imdbID)
            except: pass
        return imdbID

    def get_imdbPersonID(self, personID):
        """Translate a personID in an imdbID.
        If not in the database, try an Exact Primary Name search on IMDb;
        return None if it's unable to get the imdbID.
        """
        try: person = Name.get(personID)
        except NotFoundError: return None
        imdbID = person.imdbID
        if imdbID is not None: return '%07d' % imdbID
        n_dict = {'name': person.name, 'imdbIndex': person.imdbIndex}
        namline = build_name(n_dict, canonical=1)
        imdbID = self.name2imdbID(namline)
        if imdbID is not None:
            try: person.imdbID = int(imdbID)
            except: pass
        return imdbID

    def get_imdbCharacterID(self, characterID):
        """Translate a characterID in an imdbID.
        If not in the database, try an Exact Primary Name search on IMDb;
        return None if it's unable to get the imdbID.
        """
        try: character = CharName.get(characterID)
        except NotFoundError: return None
        imdbID = character.imdbID
        if imdbID is not None: return '%07d' % imdbID
        n_dict = {'name': character.name, 'imdbIndex': character.imdbIndex}
        namline = build_name(n_dict, canonical=1)
        imdbID = self.character2imdbID(namline)
        if imdbID is not None:
            try: character.imdbID = int(imdbID)
            except: pass
        return imdbID

    def get_imdbCompanyID(self, companyID):
        """Translate a companyID in an imdbID.
        If not in the database, try an Exact Primary Name search on IMDb;
        return None if it's unable to get the imdbID.
        """
        try: company = CompanyName.get(companyID)
        except NotFoundError: return None
        imdbID = company.imdbID
        if imdbID is not None: return '%07d' % imdbID
        n_dict = {'name': company.name, 'country': company.countryCode}
        namline = build_company_name(n_dict)
        imdbID = self.company2imdbID(namline)
        if imdbID is not None:
            try: company.imdbID = int(imdbID)
            except: pass
        return imdbID

    def do_adult_search(self, doAdult):
        """If set to 0 or False, movies in the Adult category are not
        episodeOf = title_dict.get('episode of')
        shown in the results of a search."""
        self.doAdult = doAdult

    def _search_movie(self, title, results, _episodes=False):
        title = title.strip()
        if not title: return []
        title_dict = analyze_title(title, canonical=1)
        s_title = title_dict['title']
        if not s_title: return []
        episodeOf = title_dict.get('episode of')
        if episodeOf:
            _episodes = False
        s_title_split = s_title.split(', ')
        if len(s_title_split) > 1 and \
                s_title_split[-1].lower() in _unicodeArticles:
            s_title_rebuilt = ', '.join(s_title_split[:-1])
            if s_title_rebuilt:
                s_title = s_title_rebuilt
        #if not episodeOf:
        #    if not _episodes:
        #        s_title_split = s_title.split(', ')
        #        if len(s_title_split) > 1 and \
        #                s_title_split[-1].lower() in _articles:
        #            s_title_rebuilt = ', '.join(s_title_split[:-1])
        #            if s_title_rebuilt:
        #                s_title = s_title_rebuilt
        #else:
        #    _episodes = False
        if isinstance(s_title, unicode):
            s_title = s_title.encode('ascii', 'ignore')

        soundexCode = soundex(s_title)

        # XXX: improve the search restricting the kindID if the
        #      "kind" of the input differs from "movie"?
        condition = conditionAka = None
        if _episodes:
            condition = AND(Title.q.phoneticCode == soundexCode,
                            Title.q.kindID == self._kindRev['episode'])
            conditionAka = AND(AkaTitle.q.phoneticCode == soundexCode,
                            AkaTitle.q.kindID == self._kindRev['episode'])
        elif title_dict['kind'] == 'episode' and episodeOf is not None:
            # set canonical=0 ?  Should not make much difference.
            series_title = build_title(episodeOf, canonical=1)
            # XXX: is it safe to get "results" results?
            #      Too many?  Too few?
            serRes = results
            if serRes < 3 or serRes > 10:
                serRes = 10
            searchSeries = self._search_movie(series_title, serRes)
            seriesIDs = [result[0] for result in searchSeries]
            if seriesIDs:
                condition = AND(Title.q.phoneticCode == soundexCode,
                                IN(Title.q.episodeOfID, seriesIDs),
                                Title.q.kindID == self._kindRev['episode'])
                conditionAka = AND(AkaTitle.q.phoneticCode == soundexCode,
                                IN(AkaTitle.q.episodeOfID, seriesIDs),
                                AkaTitle.q.kindID == self._kindRev['episode'])
            else:
                # XXX: bad situation: we have found no matching series;
                #      try searching everything (both episodes and
                #      non-episodes) for the title.
                condition = AND(Title.q.phoneticCode == soundexCode,
                                IN(Title.q.episodeOfID, seriesIDs))
                conditionAka = AND(AkaTitle.q.phoneticCode == soundexCode,
                                IN(AkaTitle.q.episodeOfID, seriesIDs))
        if condition is None:
            # XXX: excludes episodes?
            condition = AND(Title.q.kindID != self._kindRev['episode'],
                            Title.q.phoneticCode == soundexCode)
            conditionAka = AND(AkaTitle.q.kindID != self._kindRev['episode'],
                            AkaTitle.q.phoneticCode == soundexCode)

        # Up to 3 variations of the title are searched, plus the
        # long imdb canonical title, if provided.
        if not _episodes:
            title1, title2, title3 = titleVariations(title)
        else:
            title1 = title
            title2 = ''
            title3 = ''
        try:
            qr = [(q.id, get_movie_data(q.id, self._kind))
                    for q in Title.select(condition)]
            q2 = [(q.movieID, get_movie_data(q.id, self._kind, fromAka=1))
                    for q in AkaTitle.select(conditionAka)]
            qr += q2
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to search the database: "%s"' % str(e)

        resultsST = results * 3
        res = scan_titles(qr, title1, title2, title3, resultsST,
                            searchingEpisode=episodeOf is not None,
                            onlyEpisodes=_episodes,
                            ro_thresold=0.0)
        res[:] = [x[1] for x in res]

        if res and not self.doAdult:
            mids = [x[0] for x in res]
            genreID = self._infoRev['genres']
            adultlist = [al.movieID for al
                        in MovieInfo.select(
                            AND(MovieInfo.q.infoTypeID == genreID,
                                MovieInfo.q.info == 'Adult',
                                IN(MovieInfo.q.movieID, mids)))]
            res[:] = [x for x in res if x[0] not in adultlist]

        new_res = []
        # XXX: can there be duplicates?
        for r in res:
            if r not in q2:
                new_res.append(r)
                continue
            mdict = r[1]
            aka_title = build_title(mdict, ptdf=1)
            orig_dict = get_movie_data(r[0], self._kind)
            orig_title = build_title(orig_dict, ptdf=1)
            if aka_title == orig_title:
                new_res.append(r)
                continue
            orig_dict['akas'] = [aka_title]
            new_res.append((r[0], orig_dict))
        if results > 0: new_res[:] = new_res[:results]
        return new_res

    def _search_episode(self, title, results):
        return self._search_movie(title, results, _episodes=True)

    def get_movie_main(self, movieID):
        # Every movie information is retrieved from here.
        infosets = self.get_movie_infoset()
        try:
            res = get_movie_data(movieID, self._kind)
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to get movieID "%s": "%s"' % (movieID, str(e))
        if not res:
            raise IMDbDataAccessError, 'unable to get movieID "%s"' % movieID
        # Collect cast information.
        castdata = [[cd.personID, cd.personRoleID, cd.note, cd.nrOrder,
                    self._role[cd.roleID]]
                    for cd in CastInfo.select(CastInfo.q.movieID == movieID)]
        for p in castdata:
            person = Name.get(p[0])
            p += [person.name, person.imdbIndex]
            if p[4] in ('actor', 'actress'):
                p[4] = 'cast'
        # Regroup by role/duty (cast, writer, director, ...)
        castdata[:] =  _groupListBy(castdata, 4)
        for group in castdata:
            duty = group[0][4]
            for pdata in group:
                curRole = pdata[1]
                curRoleID = None
                if curRole is not None:
                    robj = CharName.get(curRole)
                    curRole = robj.name
                    curRoleID = robj.id
                p = Person(personID=pdata[0], name=pdata[5],
                            currentRole=curRole or u'',
                            roleID=curRoleID,
                            notes=pdata[2] or u'',
                            accessSystem='sql')
                if pdata[6]: p['imdbIndex'] = pdata[6]
                p.billingPos = pdata[3]
                res.setdefault(duty, []).append(p)
            if duty == 'cast':
                res[duty] = merge_roles(res[duty])
            res[duty].sort()
        # Info about the movie.
        minfo = [(self._info[m.infoTypeID], m.info, m.note)
                for m in MovieInfo.select(MovieInfo.q.movieID == movieID)]
        minfo += [(self._info[m.infoTypeID], m.info, m.note)
                for m in MovieInfoIdx.select(MovieInfoIdx.q.movieID == movieID)]
        minfo += [('keywords', Keyword.get(m.keywordID).keyword, None)
                for m in MovieKeyword.select(MovieKeyword.q.movieID == movieID)]
        minfo = _groupListBy(minfo, 0)
        for group in minfo:
            sect = group[0][0]
            for mdata in group:
                data = mdata[1]
                if mdata[2]: data += '::%s' % mdata[2]
                res.setdefault(sect, []).append(data)
        # Companies info about a movie.
        cinfo = [(self._compType[m.companyTypeID], m.companyID, m.note) for m
                in MovieCompanies.select(MovieCompanies.q.movieID == movieID)]
        cinfo = _groupListBy(cinfo, 0)
        for group in cinfo:
            sect = group[0][0]
            for mdata in group:
                cDb = CompanyName.get(mdata[1])
                cDbTxt = cDb.name
                if cDb.countryCode:
                    cDbTxt += ' %s' % cDb.countryCode
                company = Company(name=cDbTxt,
                                companyID=mdata[1],
                                notes=mdata[2] or u'',
                                accessSystem=self.accessSystem)
                res.setdefault(sect, []).append(company)
        # AKA titles.
        akat = [(get_movie_data(at.id, self._kind, fromAka=1), at.note)
                for at in AkaTitle.select(AkaTitle.q.movieID == movieID)]
        if akat:
            res['akas'] = []
            for td, note in akat:
                nt = build_title(td, ptdf=1)
                if note:
                    net = self._changeAKAencoding(note, nt)
                    if net is not None: nt = net
                    nt += '::%s' % note
                if nt not in res['akas']: res['akas'].append(nt)
        # Complete cast/crew.
        compcast = [(self._compcast[cc.subjectID], self._compcast[cc.statusID])
            for cc in CompleteCast.select(CompleteCast.q.movieID == movieID)]
        if compcast:
            for entry in compcast:
                val = unicode(entry[1])
                res[u'complete %s' % entry[0]] = val
        # Movie connections.
        mlinks = [[ml.linkedMovieID, self._link[ml.linkTypeID]]
                    for ml in MovieLink.select(MovieLink.q.movieID == movieID)]
        if mlinks:
            for ml in mlinks:
                lmovieData = get_movie_data(ml[0], self._kind)
                m = Movie(movieID=ml[0], data=lmovieData, accessSystem='sql')
                ml[0] = m
            res['connections'] = {}
            mlinks[:] = _groupListBy(mlinks, 1)
            for group in mlinks:
                lt = group[0][1]
                res['connections'][lt] = [i[0] for i in group]
        # Episodes.
        episodes = {}
        eps_list = list(Title.select(Title.q.episodeOfID == movieID))
        eps_list.sort()
        if eps_list:
            ps_data = {'title': res['title'], 'kind': res['kind'],
                        'year': res.get('year'),
                        'imdbIndex': res.get('imdbIndex')}
            parentSeries = Movie(movieID=movieID, data=ps_data,
                                accessSystem='sql')
            for episode in eps_list:
                episodeID = episode.id
                episode_data = get_movie_data(episodeID, self._kind)
                m = Movie(movieID=episodeID, data=episode_data,
                            accessSystem='sql')
                m['episode of'] = parentSeries
                season = episode_data.get('season', 'UNKNOWN')
                if season not in episodes: episodes[season] = {}
                ep_number = episode_data.get('episode')
                if ep_number is None:
                    ep_number = max((episodes[season].keys() or [0])) + 1
                episodes[season][ep_number] = m
            res['episodes'] = episodes
            res['number of episodes'] = sum([len(x) for x in episodes.values()])
            res['number of seasons'] = len(episodes.keys())
        # Regroup laserdisc information.
        res = _reGroupDict(res, self._moviesubs)
        # Do some transformation to preserve consistency with other
        # data access systems.
        if 'quotes' in res:
            for idx, quote in enumerate(res['quotes']):
                res['quotes'][idx] = quote.split('::')
        if 'runtimes' in res and len(res['runtimes']) > 0:
            rt = res['runtimes'][0]
            episodes = re_episodes.findall(rt)
            if episodes:
                res['runtimes'][0] = re_episodes.sub('', rt)
                if res['runtimes'][0][-2:] == '::':
                    res['runtimes'][0] = res['runtimes'][0][:-2]
        if 'votes' in res:
            res['votes'] = int(res['votes'][0])
        if 'rating' in res:
            res['rating'] = float(res['rating'][0])
        if 'votes distribution' in res:
            res['votes distribution'] = res['votes distribution'][0]
        if 'mpaa' in res:
            res['mpaa'] = res['mpaa'][0]
        if 'top 250 rank' in res:
            try: res['top 250 rank'] = int(res['top 250 rank'])
            except: pass
        if 'bottom 10 rank' in res:
            try: res['bottom 100 rank'] = int(res['bottom 10 rank'])
            except: pass
            del res['bottom 10 rank']
        for old, new in [('guest', 'guests'), ('trademarks', 'trade-mark'),
                        ('articles', 'article'), ('pictorials', 'pictorial'),
                        ('magazine-covers', 'magazine-cover-photo')]:
            if old in res:
                res[new] = res[old]
                del res[old]
        trefs,nrefs = {}, {}
        trefs,nrefs = self._extractRefs(sub_dict(res,Movie.keys_tomodify_list))
        return {'data': res, 'titlesRefs': trefs, 'namesRefs': nrefs,
                'info sets': infosets}

    # Just to know what kind of information are available.
    get_movie_alternate_versions = get_movie_main
    get_movie_business = get_movie_main
    get_movie_connections = get_movie_main
    get_movie_crazy_credits = get_movie_main
    get_movie_goofs = get_movie_main
    get_movie_keywords = get_movie_main
    get_movie_literature = get_movie_main
    get_movie_locations = get_movie_main
    get_movie_plot = get_movie_main
    get_movie_quotes = get_movie_main
    get_movie_release_dates = get_movie_main
    get_movie_soundtrack = get_movie_main
    get_movie_taglines = get_movie_main
    get_movie_technical = get_movie_main
    get_movie_trivia = get_movie_main
    get_movie_vote_details = get_movie_main
    get_movie_episodes = get_movie_main

    def _search_person(self, name, results):
        name = name.strip()
        if not name: return []
        s_name = analyze_name(name)['name']
        if not s_name: return []
        if isinstance(s_name, unicode):
            s_name = s_name.encode('ascii', 'ignore')
        soundexCode = soundex(s_name)
        name1, name2, name3 = nameVariations(name)

        # If the soundex is None, compare only with the first
        # phoneticCode column.
        if soundexCode is not None:
            condition = IN(soundexCode, [Name.q.namePcodeCf,
                                        Name.q.namePcodeNf,
                                        Name.q.surnamePcode])
            conditionAka = IN(soundexCode, [AkaName.q.namePcodeCf,
                                            AkaName.q.namePcodeNf,
                                            AkaName.q.surnamePcode])
        else:
            condition = ISNULL(Name.q.namePcodeCf)
            conditionAka = ISNULL(AkaName.q.namePcodeCf)

        try:
            qr = [(q.id, {'name': q.name, 'imdbIndex': q.imdbIndex})
                    for q in Name.select(condition)]

            q2 = [(q.personID, {'name': q.name, 'imdbIndex': q.imdbIndex})
                    for q in AkaName.select(conditionAka)]
            qr += q2
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to search the database: "%s"' % str(e)

        res = scan_names(qr, name1, name2, name3, results)
        res[:] = [x[1] for x in res]
        # Purge empty imdbIndex.
        returnl = []
        for x in res:
            tmpd = x[1]
            if tmpd['imdbIndex'] is None:
                del tmpd['imdbIndex']
            returnl.append((x[0], tmpd))

        new_res = []
        # XXX: can there be duplicates?
        for r in returnl:
            if r not in q2:
                new_res.append(r)
                continue
            pdict = r[1]
            aka_name = build_name(pdict, canonical=1)
            p = Name.get(r[0])
            orig_dict = {'name': p.name, 'imdbIndex': p.imdbIndex}
            if orig_dict['imdbIndex'] is None:
                del orig_dict['imdbIndex']
            orig_name = build_name(orig_dict, canonical=1)
            if aka_name == orig_name:
                new_res.append(r)
                continue
            orig_dict['akas'] = [aka_name]
            new_res.append((r[0], orig_dict))
        if results > 0: new_res[:] = new_res[:results]

        return new_res

    def get_person_main(self, personID):
        # Every person information is retrieved from here.
        infosets = self.get_person_infoset()
        try:
            p = Name.get(personID)
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to get personID "%s": "%s"' % (personID, str(e))
        res = {'name': p.name, 'imdbIndex': p.imdbIndex}
        if res['imdbIndex'] is None: del res['imdbIndex']
        if not res:
            raise IMDbDataAccessError, 'unable to get personID "%s"' % personID
        # Collect cast information.
        castdata = [(cd.movieID, cd.personRoleID, cd.note,
                    self._role[cd.roleID],
                    get_movie_data(cd.movieID, self._kind))
                for cd in CastInfo.select(CastInfo.q.personID == personID)]
        # Regroup by role/duty (cast, writer, director, ...)
        castdata[:] =  _groupListBy(castdata, 3)
        episodes = {}
        seenDuties = []
        for group in castdata:
            for mdata in group:
                duty = orig_duty = group[0][3]
                if duty not in seenDuties: seenDuties.append(orig_duty)
                note = mdata[2] or u''
                if 'episode of' in mdata[4]:
                    duty = 'episodes'
                    if orig_duty not in ('actor', 'actress'):
                        if note: note = ' %s' % note
                        note = '[%s]%s' % (orig_duty, note)
                curRole = mdata[1]
                curRoleID = None
                if curRole is not None:
                    robj = CharName.get(curRole)
                    curRole = robj.name
                    curRoleID = robj.id
                m = Movie(movieID=mdata[0], data=mdata[4],
                            currentRole=curRole or u'',
                            roleID=curRoleID,
                            notes=note, accessSystem='sql')
                if duty != 'episodes':
                    res.setdefault(duty, []).append(m)
                else:
                    episodes.setdefault(m['episode of'], []).append(m)
        if episodes:
            for k in episodes:
                episodes[k].sort()
                episodes[k].reverse()
            res['episodes'] = episodes
        for duty in seenDuties:
            if duty in res:
                if duty in ('actor', 'actress', 'himself', 'herself',
                            'themselves'):
                    res[duty] = merge_roles(res[duty])
                res[duty].sort()
        # Info about the person.
        pinfo = [(self._info[pi.infoTypeID], pi.info, pi.note)
                for pi in PersonInfo.select(PersonInfo.q.personID == personID)]
        # Regroup by duty.
        pinfo = _groupListBy(pinfo, 0)
        for group in pinfo:
            sect = group[0][0]
            for pdata in group:
                data = pdata[1]
                if pdata[2]: data += '::%s' % pdata[2]
                res.setdefault(sect, []).append(data)
        # AKA names.
        akan = [(an.name, an.imdbIndex)
                for an in AkaName.select(AkaName.q.personID == personID)]
        if akan:
            res['akas'] = []
            for n in akan:
                nd = {'name': n[0]}
                if n[1]: nd['imdbIndex'] = n[1]
                nt = build_name(nd, canonical=1)
                res['akas'].append(nt)
        # Do some transformation to preserve consistency with other
        # data access systems.
        for key in ('birth date', 'birth notes', 'death date', 'death notes',
                        'birth name', 'height'):
            if key in res:
                res[key] = res[key][0]
        if 'guest' in res:
            res['notable tv guest appearances'] = res['guest']
            del res['guest']
        miscnames = res.get('nick names', [])
        if 'birth name' in res: miscnames.append(res['birth name'])
        if 'akas' in res:
            for mname in miscnames:
                if mname in res['akas']: res['akas'].remove(mname)
            if not res['akas']: del res['akas']
        trefs,nrefs = self._extractRefs(sub_dict(res,Person.keys_tomodify_list))
        return {'data': res, 'titlesRefs': trefs, 'namesRefs': nrefs,
                'info sets': infosets}

    # Just to know what kind of information are available.
    get_person_filmography = get_person_main
    get_person_biography = get_person_main
    get_person_other_works = get_person_main
    get_person_episodes = get_person_main

    def _search_character(self, name, results):
        name = name.strip()
        if not name: return []
        s_name = analyze_name(name)['name']
        if not s_name: return []
        if isinstance(s_name, unicode):
            s_name = s_name.encode('ascii', 'ignore')
        s_name = normalizeName(s_name)
        soundexCode = soundex(s_name)
        surname = s_name.split(' ')[-1]
        surnameSoundex = soundex(surname)
        name2 = ''
        soundexName2 = None
        nsplit = s_name.split()
        if len(nsplit) > 1:
            name2 = '%s %s' % (nsplit[-1], ' '.join(nsplit[:-1]))
            if s_name == name2:
                name2 = ''
            else:
                soundexName2 = soundex(name2)
        # If the soundex is None, compare only with the first
        # phoneticCode column.
        if soundexCode is not None:
            if soundexName2 is not None:
                condition = OR(surnameSoundex == CharName.q.surnamePcode,
                            IN(CharName.q.namePcodeNf, [soundexCode,
                                                        soundexName2]),
                            IN(CharName.q.surnamePcode, [soundexCode,
                                                        soundexName2]))
            else:
                condition = OR(surnameSoundex == CharName.q.surnamePcode,
                            IN(soundexCode, [CharName.q.namePcodeNf,
                                            CharName.q.surnamePcode]))
        else:
            condition = ISNULL(Name.q.namePcodeNf)
        try:
            qr = [(q.id, {'name': q.name, 'imdbIndex': q.imdbIndex})
                    for q in CharName.select(condition)]
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to search the database: "%s"' % str(e)
        res = scan_names(qr, s_name, name2, '', results,
                        _scan_character=True)
        res[:] = [x[1] for x in res]
        # Purge empty imdbIndex.
        returnl = []
        for x in res:
            tmpd = x[1]
            if tmpd['imdbIndex'] is None:
                del tmpd['imdbIndex']
            returnl.append((x[0], tmpd))
        return returnl

    def get_character_main(self, characterID, results=1000):
        # Every character information is retrieved from here.
        infosets = self.get_character_infoset()
        try:
            c = CharName.get(characterID)
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to get characterID "%s": "%s"' % (characterID, e)
        res = {'name': c.name, 'imdbIndex': c.imdbIndex}
        if res['imdbIndex'] is None: del res['imdbIndex']
        if not res:
            raise IMDbDataAccessError, 'unable to get characterID "%s"' % \
                                        characterID
        # Collect filmography information.
        items = CastInfo.select(CastInfo.q.personRoleID == characterID)
        if results > 0:
            items = items[:results]
        filmodata = [(cd.movieID, cd.personID, cd.note,
                    get_movie_data(cd.movieID, self._kind)) for cd in items
                    if self._role[cd.roleID] in ('actor', 'actress')]
        fdata = []
        for f in filmodata:
            curRole = None
            curRoleID = f[1]
            note = f[2] or u''
            if curRoleID is not None:
                robj = Name.get(curRoleID)
                curRole = robj.name
            m = Movie(movieID=f[0], data=f[3],
                        currentRole=curRole or u'',
                        roleID=curRoleID, roleIsPerson=True,
                        notes=note, accessSystem='sql')
            fdata.append(m)
        fdata = merge_roles(fdata)
        fdata.sort()
        if fdata:
            res['filmography'] = fdata
        return {'data': res, 'info sets': infosets}

    get_character_filmography = get_character_main
    get_character_biography = get_character_main

    def _search_company(self, name, results):
        name = name.strip()
        if not name: return []
        if isinstance(name, unicode):
            name = name.encode('ascii', 'ignore')
        soundexCode = soundex(name)
        # If the soundex is None, compare only with the first
        # phoneticCode column.
        if soundexCode is None:
            condition = ISNULL(CompanyName.q.namePcodeNf)
        else:
            if name.endswith(']'):
                condition = CompanyName.q.namePcodeSf == soundexCode
            else:
                condition = CompanyName.q.namePcodeNf == soundexCode
        try:
            qr = [(q.id, {'name': q.name, 'country': q.countryCode})
                    for q in CompanyName.select(condition)]
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to search the database: "%s"' % str(e)
        qr[:] = [(x[0], build_company_name(x[1])) for x in qr]
        res = scan_company_names(qr, name, results)
        res[:] = [x[1] for x in res]
        # Purge empty country keys.
        returnl = []
        for x in res:
            tmpd = x[1]
            country = tmpd.get('country')
            if country is None and 'country' in tmpd:
                del tmpd['country']
            returnl.append((x[0], tmpd))
        return returnl

    def get_company_main(self, companyID, results=0):
        # Every company information is retrieved from here.
        infosets = self.get_company_infoset()
        try:
            c = CompanyName.get(companyID)
        except NotFoundError, e:
            raise IMDbDataAccessError, \
                    'unable to get companyID "%s": "%s"' % (companyID, e)
        res = {'name': c.name, 'country': c.countryCode}
        if res['country'] is None: del res['country']
        if not res:
            raise IMDbDataAccessError, 'unable to get companyID "%s"' % \
                                        companyID
        # Collect filmography information.
        items = MovieCompanies.select(MovieCompanies.q.companyID == companyID)
        if results > 0:
            items = items[:results]
        filmodata = [(cd.movieID, cd.companyID,
                    self._compType[cd.companyTypeID], cd.note,
                    get_movie_data(cd.movieID, self._kind)) for cd in items]
        filmodata = _groupListBy(filmodata, 2)
        for group in filmodata:
            ctype = group[0][2]
            for movieID, companyID, ctype, note, movieData in group:
                movie = Movie(data=movieData, movieID=movieID,
                            notes=note or u'', accessSystem=self.accessSystem)
                res.setdefault(ctype, []).append(movie)
            res.get(ctype, []).sort()
        return {'data': res, 'info sets': infosets}

    def _search_keyword(self, keyword, results):
        constr = OR(Keyword.q.phoneticCode ==
                    soundex(keyword.encode('ascii', 'ignore')),
                    CONTAINSSTRING(Keyword.q.keyword, self.toUTF8(keyword)))
        return filterSimilarKeywords(keyword,
                        _iterKeywords(Keyword.select(constr)))[:results]

    def _get_keyword(self, keyword, results):
        keyID = Keyword.select(Keyword.q.keyword == keyword)
        if keyID.count() == 0:
            return []
        keyID = keyID[0].id
        movies = MovieKeyword.select(MovieKeyword.q.keywordID ==
                                    keyID)[:results]
        return [(m.movieID, get_movie_data(m.movieID, self._kind))
                for m in movies]

    def _get_top_bottom_movies(self, kind):
        if kind == 'top':
            kind = 'top 250 rank'
        elif kind == 'bottom':
            # Not a refuse: the plain text data files contains only
            # the bottom 10 movies.
            kind = 'bottom 10 rank'
        else:
            return []
        infoID = InfoType.select(InfoType.q.info == kind)
        if infoID.count() == 0:
            return []
        infoID = infoID[0].id
        movies = MovieInfoIdx.select(MovieInfoIdx.q.infoTypeID == infoID)
        ml = []
        for m in movies:
            minfo = get_movie_data(m.movieID, self._kind)
            for k in kind, 'votes', 'rating', 'votes distribution':
                valueDict = getSingleInfo(MovieInfoIdx, m.movieID,
                                            k, notAList=True)
                if k in (kind, 'votes') and k in valueDict:
                    valueDict[k] = int(valueDict[k])
                elif k == 'rating' and k in valueDict:
                    valueDict[k] = float(valueDict[k])
                minfo.update(valueDict)
            ml.append((m.movieID, minfo))
        sorter = (_cmpBottom, _cmpTop)[kind == 'top 250 rank']
        ml.sort(sorter)
        return ml

    def __del__(self):
        """Ensure that the connection is closed."""
        if not hasattr(self, '_connection'): return
        self._sql_logger.debug('closing connection to the database')
        self._connection.close()

