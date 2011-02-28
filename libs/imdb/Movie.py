"""
Movie module (imdb package).

This module provides the Movie class, used to store information about
a given movie.

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

from imdb import articles
from imdb.utils import analyze_title, build_title, canonicalTitle, \
                        flatten, _Container, cmpMovies


class Movie(_Container):
    """A Movie.

    Every information about a movie can be accessed as:
        movieObject['information']
    to get a list of the kind of information stored in a
    Movie object, use the keys() method; some useful aliases
    are defined (as "casting" for the "casting director" key); see
    the keys_alias dictionary.
    """
    # The default sets of information retrieved.
    default_info = ('main', 'plot')

    # Aliases for some not-so-intuitive keys.
    keys_alias = {
                'tv schedule': 'airing',
                'user rating':  'rating',
                'plot summary': 'plot',
                'plot summaries': 'plot',
                'directed by':  'director',
                'created by': 'creator',
                'writing credits': 'writer',
                'produced by':  'producer',
                'original music by':    'original music',
                'non-original music by':    'non-original music',
                'music':    'original music',
                'cinematography by':    'cinematographer',
                'cinematography':   'cinematographer',
                'film editing by':  'editor',
                'film editing': 'editor',
                'editing':  'editor',
                'actors':   'cast',
                'actresses':    'cast',
                'casting by':   'casting director',
                'casting':  'casting director',
                'art direction by': 'art direction',
                'set decoration by':    'set decoration',
                'costume design by':    'costume designer',
                'costume design':    'costume designer',
                'makeup department':    'make up',
                'makeup':    'make up',
                'make-up':    'make up',
                'production management':    'production manager',
                'production company':    'production companies',
                'second unit director or assistant director':
                                                'assistant director',
                'second unit director':   'assistant director',
                'sound department': 'sound crew',
                'costume and wardrobe department': 'costume department',
                'special effects by':   'special effects',
                'visual effects by':    'visual effects',
                'special effects company':   'special effects companies',
                'stunts':   'stunt performer',
                'other crew':   'miscellaneous crew',
                'misc crew':   'miscellaneous crew',
                'miscellaneouscrew':   'miscellaneous crew',
                'crewmembers': 'miscellaneous crew',
                'crew members': 'miscellaneous crew',
                'other companies': 'miscellaneous companies',
                'misc companies': 'miscellaneous companies',
                'miscellaneous company': 'miscellaneous companies',
                'misc company': 'miscellaneous companies',
                'other company': 'miscellaneous companies',
                'aka':  'akas',
                'also known as':    'akas',
                'country':  'countries',
                'production country':  'countries',
                'production countries':  'countries',
                'genre': 'genres',
                'runtime':  'runtimes',
                'lang': 'languages',
                'color': 'color info',
                'cover': 'cover url',
                'full-size cover': 'full-size cover url',
                'seasons': 'number of seasons',
                'language': 'languages',
                'certificate':  'certificates',
                'certifications':   'certificates',
                'certification':    'certificates',
                'miscellaneous links':  'misc links',
                'miscellaneous':    'misc links',
                'soundclips':   'sound clips',
                'videoclips':   'video clips',
                'photographs':  'photo sites',
                'distributor': 'distributors',
                'distribution': 'distributors',
                'distribution companies': 'distributors',
                'distribution company': 'distributors',
                'guest': 'guests',
                'guest appearances': 'guests',
                'tv guests': 'guests',
                'notable tv guest appearances': 'guests',
                'episodes cast': 'guests',
                'episodes number': 'number of episodes',
                'amazon review': 'amazon reviews',
                'merchandising': 'merchandising links',
                'merchandise': 'merchandising links',
                'sales': 'merchandising links',
                'faq': 'faqs',
                'parental guide': 'parents guide',
                'frequently asked questions': 'faqs'}

    keys_tomodify_list = ('plot', 'trivia', 'alternate versions', 'goofs',
                        'quotes', 'dvd', 'laserdisc', 'news', 'soundtrack',
                        'crazy credits', 'business', 'supplements',
                        'video review', 'faqs')

    cmpFunct = cmpMovies

    def _init(self, **kwds):
        """Initialize a Movie object.

        *movieID* -- the unique identifier for the movie.
        *title* -- the title of the Movie, if not in the data dictionary.
        *myTitle* -- your personal title for the movie.
        *myID* -- your personal identifier for the movie.
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
        *notes* -- notes for the person referred in the currentRole
                    attribute; e.g.: '(voice)'.
        *accessSystem* -- a string representing the data access system used.
        *titlesRefs* -- a dictionary with references to movies.
        *namesRefs* -- a dictionary with references to persons.
        *charactersRefs* -- a dictionary with references to characters.
        *modFunct* -- function called returning text fields.
        """
        title = kwds.get('title')
        if title and not self.data.has_key('title'):
            self.set_title(title)
        self.movieID = kwds.get('movieID', None)
        self.myTitle = kwds.get('myTitle', u'')

    def _reset(self):
        """Reset the Movie object."""
        self.movieID = None
        self.myTitle = u''

    def set_title(self, title):
        """Set the title of the movie."""
        # XXX: convert title to unicode, if it's a plain string?
        d_title = analyze_title(title)
        self.data.update(d_title)

    def _additional_keys(self):
        """Valid keys to append to the data.keys() list."""
        addkeys = []
        if self.data.has_key('title'):
            addkeys += ['canonical title', 'long imdb title',
                        'long imdb canonical title',
                        'smart canonical title',
                        'smart long imdb canonical title']
        if self.data.has_key('episode of'):
            addkeys += ['long imdb episode title', 'series title',
                        'canonical series title', 'episode title',
                        'canonical episode title',
                        'smart canonical series title',
                        'smart canonical episode title']
        if self.data.has_key('cover url'):
            addkeys += ['full-size cover url']
        return addkeys

    def guessLanguage(self):
        """Guess the language of the title of this movie; returns None
        if there are no hints."""
        lang = self.get('languages')
        if lang:
            lang = lang[0]
        else:
            country = self.get('countries')
            if country:
                lang = articles.COUNTRY_LANG.get(country[0])
        return lang

    def smartCanonicalTitle(self, title=None, lang=None):
        """Return the canonical title, guessing its language.
        The title can be forces with the 'title' argument (internally
        used) and the language can be forced with the 'lang' argument,
        otherwise it's auto-detected."""
        if title is None:
            title = self.data.get('title', u'')
        if lang is None:
            lang = self.guessLanguage()
        return canonicalTitle(title, lang=lang)

    def _getitem(self, key):
        """Handle special keys."""
        if self.data.has_key('episode of'):
            if key == 'long imdb episode title':
                return build_title(self.data)
            elif key == 'series title':
                return self.data['episode of']['title']
            elif key == 'canonical series title':
                ser_title = self.data['episode of']['title']
                return canonicalTitle(ser_title)
            elif key == 'smart canonical series title':
                ser_title = self.data['episode of']['title']
                return self.smartCanonicalTitle(ser_title)
            elif key == 'episode title':
                return self.data.get('title', u'')
            elif key == 'canonical episode title':
                return canonicalTitle(self.data.get('title', u''))
            elif key == 'smart canonical episode title':
                return self.smartCanonicalTitle(self.data.get('title', u''))
        if self.data.has_key('title'):
            if key == 'title':
                return self.data['title']
            elif key == 'long imdb title':
                return build_title(self.data)
            elif key == 'canonical title':
                return canonicalTitle(self.data['title'])
            elif key == 'smart canonical title':
                return self.smartCanonicalTitle(self.data['title'])
            elif key == 'long imdb canonical title':
                return build_title(self.data, canonical=1)
            elif key == 'smart long imdb canonical title':
                return build_title(self.data, canonical=1,
                                    lang=self.guessLanguage())
        if key == 'full-size cover url' and self.data.has_key('cover url'):
            return self._re_fullsizeURL.sub('', self.data.get('cover url', ''))
        return None

    def getID(self):
        """Return the movieID."""
        return self.movieID

    def __nonzero__(self):
        """The Movie is "false" if the self.data does not contain a title."""
        # XXX: check the title and the movieID?
        if self.data.has_key('title'): return 1
        return 0

    def isSameTitle(self, other):
        """Return true if this and the compared object have the same
        long imdb title and/or movieID.
        """
        # XXX: obsolete?
        if not isinstance(other, self.__class__): return 0
        if self.data.has_key('title') and \
                other.data.has_key('title') and \
                build_title(self.data, canonical=0) == \
                build_title(other.data, canonical=0):
            return 1
        if self.accessSystem == other.accessSystem and \
                self.movieID is not None and self.movieID == other.movieID:
            return 1
        return 0
    isSameMovie = isSameTitle # XXX: just for backward compatiblity.

    def __contains__(self, item):
        """Return true if the given Person object is listed in this Movie,
        or if the the given Character is represented in this Movie."""
        from Person import Person
        from Character import Character
        from Company import Company
        if isinstance(item, Person):
            for p in flatten(self.data, yieldDictKeys=1, scalar=Person,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(p):
                    return 1
        elif isinstance(item, Character):
            for p in flatten(self.data, yieldDictKeys=1, scalar=Person,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(p.currentRole):
                    return 1
        elif isinstance(item, Company):
            for c in flatten(self.data, yieldDictKeys=1, scalar=Company,
                            toDescend=(list, dict, tuple, Movie)):
                if item.isSame(c):
                    return 1
        return 0

    def __deepcopy__(self, memo):
        """Return a deep copy of a Movie instance."""
        m = Movie(title=u'', movieID=self.movieID, myTitle=self.myTitle,
                    myID=self.myID, data=deepcopy(self.data, memo),
                    currentRole=deepcopy(self.currentRole, memo),
                    roleIsPerson=self._roleIsPerson,
                    notes=self.notes, accessSystem=self.accessSystem,
                    titlesRefs=deepcopy(self.titlesRefs, memo),
                    namesRefs=deepcopy(self.namesRefs, memo),
                    charactersRefs=deepcopy(self.charactersRefs, memo))
        m.current_info = list(self.current_info)
        m.set_mod_funct(self.modFunct)
        return m

    def __repr__(self):
        """String representation of a Movie object."""
        # XXX: add also currentRole and notes, if present?
        if self.has_key('long imdb episode title'):
            title = self.get('long imdb episode title')
        else:
            title = self.get('long imdb title')
        r = '<Movie id:%s[%s] title:_%s_>' % (self.movieID, self.accessSystem,
                                                title)
        if isinstance(r, unicode): r = r.encode('utf_8', 'replace')
        return r

    def __str__(self):
        """Simply print the short title."""
        return self.get('title', u'').encode('utf_8', 'replace')

    def __unicode__(self):
        """Simply print the short title."""
        return self.get('title', u'')

    def summary(self):
        """Return a string with a pretty-printed summary for the movie."""
        if not self: return u''
        def _nameAndRole(personList, joiner=u', '):
            """Build a pretty string with name and role."""
            nl = []
            for person in personList:
                n = person.get('name', u'')
                if person.currentRole: n += u' (%s)' % person.currentRole
                nl.append(n)
            return joiner.join(nl)
        s = u'Movie\n=====\nTitle: %s\n' % \
                    self.get('long imdb canonical title', u'')
        genres = self.get('genres')
        if genres: s += u'Genres: %s.\n' % u', '.join(genres)
        director = self.get('director')
        if director:
            s += u'Director: %s.\n' % _nameAndRole(director)
        writer = self.get('writer')
        if writer:
            s += u'Writer: %s.\n' % _nameAndRole(writer)
        cast = self.get('cast')
        if cast:
            cast = cast[:5]
            s += u'Cast: %s.\n' % _nameAndRole(cast)
        runtime = self.get('runtimes')
        if runtime:
            s += u'Runtime: %s.\n' % u', '.join(runtime)
        countries = self.get('countries')
        if countries:
            s += u'Country: %s.\n' % u', '.join(countries)
        lang = self.get('languages')
        if lang:
            s += u'Language: %s.\n' % u', '.join(lang)
        rating = self.get('rating')
        if rating:
            s += u'Rating: %s' % rating
            nr_votes = self.get('votes')
            if nr_votes:
                s += u' (%s votes)' % nr_votes
            s += u'.\n'
        plot = self.get('plot')
        if not plot:
            plot = self.get('plot summary')
            if plot:
                plot = [plot]
        if plot:
            plot = plot[0]
            i = plot.find('::')
            if i != -1:
                plot = plot[:i]
            s += u'Plot: %s' % plot
        return s


