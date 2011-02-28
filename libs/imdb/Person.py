"""
Person module (imdb package).

This module provides the Person class, used to store information about
a given person.

Copyright 2004-2010 Davide Alberani <da@erlug.linux.it>

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

from copy import deepcopy

from imdb.utils import analyze_name, build_name, normalizeName, \
                        flatten, _Container, cmpPeople


class Person(_Container):
    """A Person.

    Every information about a person can be accessed as:
        personObject['information']
    to get a list of the kind of information stored in a
    Person object, use the keys() method; some useful aliases
    are defined (as "biography" for the "mini biography" key);
    see the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main', 'filmography', 'biography')

    # Aliases for some not-so-intuitive keys.
    keys_alias = {'biography': 'mini biography',
                  'bio': 'mini biography',
                  'aka': 'akas',
                  'also known as': 'akas',
                  'nick name': 'nick names',
                  'nicks': 'nick names',
                  'nickname': 'nick names',
                  'miscellaneouscrew': 'miscellaneous crew',
                  'crewmembers': 'miscellaneous crew',
                  'misc': 'miscellaneous crew',
                  'guest': 'notable tv guest appearances',
                  'guests': 'notable tv guest appearances',
                  'tv guest': 'notable tv guest appearances',
                  'guest appearances': 'notable tv guest appearances',
                  'spouses': 'spouse',
                  'salary': 'salary history',
                  'salaries': 'salary history',
                  'otherworks': 'other works',
                  "maltin's biography":
                        "biography from leonard maltin's movie encyclopedia",
                  "leonard maltin's biography":
                        "biography from leonard maltin's movie encyclopedia",
                  'real name': 'birth name',
                  'where are they now': 'where now',
                  'personal quotes': 'quotes',
                  'mini-biography author': 'imdb mini-biography by',
                  'biography author': 'imdb mini-biography by',
                  'genre': 'genres',
                  'portrayed': 'portrayed in',
                  'keys': 'keywords',
                  'trademarks': 'trade mark',
                  'trade mark': 'trade mark',
                  'trade marks': 'trade mark',
                  'trademark': 'trade mark',
                  'pictorials': 'pictorial',
                  'magazine covers': 'magazine cover photo',
                  'magazine-covers': 'magazine cover photo',
                  'tv series episodes': 'episodes',
                  'tv-series episodes': 'episodes',
                  'articles': 'article',
                  'keyword': 'keywords'}

    # 'nick names'???
    keys_tomodify_list = ('mini biography', 'spouse', 'quotes', 'other works',
                        'salary history', 'trivia', 'trade mark', 'news',
                        'books', 'biographical movies', 'portrayed in',
                        'where now', 'interviews', 'article',
                        "biography from leonard maltin's movie encyclopedia")

    cmpFunct = cmpPeople

    def _init(self, **kwds):
        """Initialize a Person object.

        *personID* -- the unique identifier for the person.
        *name* -- the name of the Person, if not in the data dictionary.
        *myName* -- the nickname you use for this person.
        *myID* -- your personal id for this person.
        *data* -- a dictionary used to initialize the object.
        *currentRole* -- a Character instance representing the current role
                         or duty of a person in this movie, or a Person
                         object representing the actor/actress who played
                         a given character in a Movie.  If a string is
                         passed, an object is automatically build.
        *roleID* -- if available, the characterID/personID of the currentRole
                    object.
        *roleIsPerson* -- when False (default) the currentRole is assumed
                          to be a Character object, otherwise a Person.
        *notes* -- notes about the given person for a specific movie
                    or role (e.g.: the alias used in the movie credits).
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *modFunct* -- function called returning text fields.
        *billingPos* -- position of this person in the credits list.
        """
        name = kwds.get('name')
        if name and not self.data.has_key('name'):
            self.set_name(name)
        self.personID = kwds.get('personID', None)
        self.myName = kwds.get('myName', u'')
        self.billingPos = kwds.get('billingPos', None)

    def _reset(self):
        """Reset the Person object."""
        self.personID = None
        self.myName = u''
        self.billingPos = None

    def _clear(self):
        """Reset the dictionary."""
        self.billingPos = None

    def set_name(self, name):
        """Set the name of the person."""
        # XXX: convert name to unicode, if it's a plain string?
        d = analyze_name(name, canonical=1)
        self.data.update(d)

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        addkeys = []
        if self.data.has_key('name'):
            addkeys += ['canonical name', 'long imdb name',
                        'long imdb canonical name']
        if self.data.has_key('headshot'):
            addkeys += ['full-size headshot']
        return addkeys

    def _getitem(self, key):
        """Handle special keys."""
        if self.data.has_key('name'):
            if key == 'name':
                return normalizeName(self.data['name'])
            elif key == 'canonical name':
                return self.data['name']
            elif key == 'long imdb name':
                return build_name(self.data, canonical=0)
            elif key == 'long imdb canonical name':
                return build_name(self.data)
        if key == 'full-size headshot' and self.data.has_key('headshot'):
            return self._re_fullsizeURL.sub('', self.data.get('headshot', ''))
        return None

    def getID(self):
        """Return the personID."""
        return self.personID

    def __nonzero__(self):
        """The Person is "false" if the self.data does not contain a name."""
        # XXX: check the name and the personID?
        if self.data.has_key('name'): return 1
        return 0

    def __contains__(self, item):
        """Return true if this Person has worked in the given Movie,
        or if the fiven Character was played by this Person."""
        from Movie import Movie
        from Character import Character
        if isinstance(item, Movie):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m):
                    return 1
        elif isinstance(item, Character):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m.currentRole):
                    return 1
        return 0

    def isSameName(self, other):
        """Return true if two persons have the same name and imdbIndex
        and/or personID.
        """
        if not isinstance(other, self.__class__):
            return 0
        if self.data.has_key('name') and \
                other.data.has_key('name') and \
                build_name(self.data, canonical=1) == \
                build_name(other.data, canonical=1):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.personID and self.personID == other.personID:
            return 1
        return 0
    isSamePerson = isSameName # XXX: just for backward compatiblity.

    def __deepcopy__(self, memo):
        """Return a deep copy of a Person instance."""
        p = Person(name=u'', personID=self.personID, myName=self.myName,
                    myID=self.myID, data=deepcopy(self.data, memo),
                    currentRole=deepcopy(self.currentRole, memo),
                    roleIsPerson=self._roleIsPerson,
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        p.current_info = list(self.current_info)
        p.set_mod_funct(self.modFunct)
        p.billingPos = self.billingPos
        return p

    def __repr__(self):
        """String representation of a Person object."""
        # XXX: add also currentRole and notes, if present?
        r = '<Person id:%s[%s] name:_%s_>' % (self.personID, self.accessSystem,
                                        self.get('long imdb canonical name'))
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short name."""
        return self.get('name', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('name', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the person."""
        if not self: return u''
        s = u'Person\n=====\nName: %s\n' % \
                                self.get('long imdb canonical name', u'')
        bdate = self.get('birth date')
        if bdate:
            s += u'Birth date: %s' % bdate
            bnotes = self.get('birth notes')
            if bnotes:
                s += u' (%s)' % bnotes
            s += u'.\n'
        ddate = self.get('death date')
        if ddate:
            s += u'Death date: %s' % ddate
            dnotes = self.get('death notes')
            if dnotes:
                s += u' (%s)' % dnotes
            s += u'.\n'
        bio = self.get('mini biography')
        if bio:
            s += u'Biography: %s\n' % bio[0]
        director = self.get('director')
        if director:
            d_list = [x.get('long imdb canonical title', u'')
                        for x in director[:3]]
            s += u'Last movies directed: %s.\n' % u'; '.join(d_list)
        act = self.get('actor') or self.get('actress')
        if act:
            a_list = [x.get('long imdb canonical title', u'')
                        for x in act[:5]]
            s += u'Last movies acted: %s.\n' % u'; '.join(a_list)
        return s


