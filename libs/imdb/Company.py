"""
company module (imdb package).

This module provides the company class, used to store information about
a given company.

Copyright 2008-2009 Davide Alberani <da@erlug.linux.it>

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

from imdb.utils import analyze_company_name, build_company_name, \
                        flatten, _Container, cmpCompanies


class Company(_Container):
    """A company.

    Every information about a company can be accessed as:
        companyObject['information']
    to get a list of the kind of information stored in a
    company object, use the keys() method; some useful aliases
    are defined (as "also known as" for the "akas" key);
    see the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main',)

    # Aliases for some not-so-intuitive keys.
    keys_alias = {
            'distributor': 'distributors',
            'special effects company': 'special effects companies',
            'other company': 'miscellaneous companies',
            'miscellaneous company': 'miscellaneous companies',
            'other companies': 'miscellaneous companies',
            'misc companies': 'miscellaneous companies',
            'misc company': 'miscellaneous companies',
            'production company': 'production companies'}

    keys_tomodify_list = ()

    cmpFunct = cmpCompanies

    def _init(self, **kwds):
        """Initialize a company object.

        *companyID* -- the unique identifier for the company.
        *name* -- the name of the company, if not in the data dictionary.
        *myName* -- the nickname you use for this company.
        *myID* -- your personal id for this company.
        *data* -- a dictionary used to initialize the object.
        *notes* -- notes about the given company.
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to companies.
        *modFunct* -- function called returning text fields.
        """
        name = kwds.get('name')
        if name and not self.data.has_key('name'):
            self.set_name(name)
        self.companyID = kwds.get('companyID', None)
        self.myName = kwds.get('myName', u'')

    def _reset(self):
        """Reset the company object."""
        self.companyID = None
        self.myName = u''

    def set_name(self, name):
        """Set the name of the company."""
        # XXX: convert name to unicode, if it's a plain string?
        # Company diverges a bit from other classes, being able
        # to directly handle its "notes".  AND THAT'S PROBABLY A BAD IDEA!
        oname = name = name.strip()
        notes = u''
        if name.endswith(')'):
            fparidx = name.find('(')
            if fparidx != -1:
                notes = name[fparidx:]
                name = name[:fparidx].rstrip()
        if self.notes:
            name = oname
        d = analyze_company_name(name)
        self.data.update(d)
        if notes and not self.notes:
            self.notes = notes

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        if self.data.has_key('name'):
            return ['long imdb name']
        return []

    def _getitem(self, key):
        """Handle special keys."""
        ## XXX: can a company have an imdbIndex?
        if self.data.has_key('name'):
            if key == 'long imdb name':
                return build_company_name(self.data)
        return None

    def getID(self):
        """Return the companyID."""
        return self.companyID

    def __nonzero__(self):
        """The company is "false" if the self.data does not contain a name."""
        # XXX: check the name and the companyID?
        if self.data.get('name'): return 1
        return 0

    def __contains__(self, item):
        """Return true if this company and the given Movie are related."""
        from Movie import Movie
        if isinstance(item, Movie):
            for m in flatten(self.data, yieldDictKeys=1, scalar=Movie):
                if item.isSame(m):
                    return 1
        return 0

    def isSameName(self, other):
        """Return true if two company have the same name
        and/or companyID."""
        if not isinstance(other, self.__class__):
            return 0
        if self.data.has_key('name') and \
                other.data.has_key('name') and \
                build_company_name(self.data) == \
                build_company_name(other.data):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.companyID is not None and \
                self.companyID == other.companyID:
            return 1
        return 0
    isSameCompany = isSameName

    def __deepcopy__(self, memo):
        """Return a deep copy of a company instance."""
        c = Company(name=u'', companyID=self.companyID,
                    myName=self.myName, myID=self.myID,
                    data=deepcopy(self.data, memo),
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        c.current_info = list(self.current_info)
        c.set_mod_funct(self.modFunct)
        return c

    def __repr__(self):
        """String representation of a Company object."""
        r = '<Company id:%s[%s] name:_%s_>' % (self.companyID,
                                        self.accessSystem,
                                        self.get('long imdb name'))
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short name."""
        return self.get('name', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('name', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the company."""
        if not self: return u''
        s = u'Company\n=======\nName: %s\n' % \
                                self.get('name', u'')
        for k in ('distributor', 'production company', 'miscellaneous company',
                'special effects company'):
            d = self.get(k, [])[:5]
            if not d: continue
            s += u'Last movies from this company (%s): %s.\n' % \
                    (k, u'; '.join([x.get('long imdb title', u'') for x in d]))
        return s


