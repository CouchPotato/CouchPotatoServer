#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from guessit import fileutils
import logging

log = logging.getLogger('guessit.language')

# downloaded from http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
#
# Description of the fields:
# "An alpha-3 (bibliographic) code, an alpha-3 (terminologic) code (when given),
# an alpha-2 code (when given), an English name, and a French name of a language
# are all separated by pipe (|) characters."
_iso639_contents = fileutils.load_file_in_same_dir(__file__,
                                                   'ISO-639-2_utf-8.txt')
language_matrix = [ l.strip().decode('utf-8').split('|')
                    for l in _iso639_contents.split('\n') ]

lng3        = frozenset(l[0] for l in language_matrix if l[0])
lng3term    = frozenset(l[1] for l in language_matrix if l[1])
lng2        = frozenset(l[2] for l in language_matrix if l[2])
lng_en_name = frozenset(lng for l in language_matrix
                        for lng in l[3].lower().split('; ') if lng)
lng_fr_name = frozenset(lng for l in language_matrix
                        for lng in l[4].lower().split('; ') if lng)
lng_all_names = lng3 | lng3term | lng2 | lng_en_name | lng_fr_name

lng3_to_lng3term = dict((l[0], l[1]) for l in language_matrix if l[1])
lng3term_to_lng3 = dict((l[1], l[0]) for l in language_matrix if l[1])

lng3_to_lng2 = dict((l[0], l[2]) for l in language_matrix if l[2])
lng2_to_lng3 = dict((l[2], l[0]) for l in language_matrix if l[2])

# we only return the first given english name, hoping it is the most used one
lng3_to_lng_en_name = dict((l[0], l[3].split('; ')[0])
                           for l in language_matrix if l[3])
lng_en_name_to_lng3 = dict((en_name.lower(), l[0])
                           for l in language_matrix if l[3]
                           for en_name in l[3].split('; '))

# we only return the first given french name, hoping it is the most used one
lng3_to_lng_fr_name = dict((l[0], l[4].split('; ')[0])
                           for l in language_matrix if l[4])
lng_fr_name_to_lng3 = dict((fr_name.lower(), l[0])
                           for l in language_matrix if l[4]
                           for fr_name in l[4].split('; '))


def is_language(language):
    return language.lower() in lng_all_names


class Language(object):
    """This class represents a human language.

    You can initialize it with pretty much everything, as it knows conversion
    from ISO-639 2-letter and 3-letter codes, English and French names.

    >>> Language('fr')
    Language(French)

    >>> Language('eng').french_name()
    u'anglais'
    """
    def __init__(self, language):
        lang = None
        language = language.lower()
        if len(language) == 2:
            lang = lng2_to_lng3.get(language)
        elif len(language) == 3:
            lang = (language
                    if language in lng3
                    else lng3term_to_lng3.get(language))
        else:
            lang = (lng_en_name_to_lng3.get(language) or
                    lng_fr_name_to_lng3.get(language))

        if lang is None:
            msg = 'The given string "%s" could not be identified as a language'
            raise ValueError(msg % language)

        self.lang = lang

    def lng2(self):
        return lng3_to_lng2[self.lang]

    def lng3(self):
        return self.lang

    def lng3term(self):
        return lng3_to_lng3term[self.lang]

    def english_name(self):
        return lng3_to_lng_en_name[self.lang]

    def french_name(self):
        return lng3_to_lng_fr_name[self.lang]

    def __hash__(self):
        return hash(self.lang)

    def __eq__(self, other):
        if isinstance(other, Language):
            return self.lang == other.lang

        if isinstance(other, basestring):
            try:
                return self == Language(other)
            except ValueError:
                return False

        return False

    def __ne__(self, other):
        return not self == other

    def __unicode__(self):
        return lng3_to_lng_en_name[self.lang]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return 'Language(%s)' % self


def search_language(string, lang_filter=None):
    """Looks for language patterns, and if found return the language object,
    its group span and an associated confidence.

    you can specify a list of allowed languages using the lang_filter argument,
    as in lang_filter = [ 'fr', 'eng', 'spanish' ]

    >>> search_language('movie [en].avi')
    (Language(English), (7, 9), 0.8)

    >>> search_language('the zen fat cat and the gay mad men got a new fan', lang_filter = ['en', 'fr', 'es'])
    (None, None, None)
    """

    # list of common words which could be interpreted as languages, but which
    # are far too common to be able to say they represent a language in the
    # middle of a string (where they most likely carry their commmon meaning)
    lng_common_words = frozenset([
        # english words
        'is', 'it', 'am', 'mad', 'men', 'man', 'run', 'sin', 'st', 'to',
        'no', 'non', 'war', 'min', 'new', 'car', 'day', 'bad', 'bat', 'fan',
        'fry', 'cop', 'zen', 'gay', 'fat', 'cherokee', 'got', 'an', 'as',
        'cat', 'her', 'be', 'hat', 'sun', 'may', 'my', 'mr',
        # french words
        'bas', 'de', 'le', 'son', 'vo', 'vf', 'ne', 'ca', 'ce', 'et', 'que',
        'mal', 'est', 'vol', 'or', 'mon', 'se',
        # spanish words
        'la', 'el', 'del', 'por', 'mar',
        # other
        'ind', 'arw', 'ts', 'ii', 'bin', 'chan', 'ss', 'san', 'oss', 'iii',
        'vi'
        ])
    sep = r'[](){} \._-+'

    if lang_filter:
        lang_filter = set(Language(l) for l in lang_filter)

    slow = ' %s ' % string.lower()
    confidence = 1.0 # for all of them
    for lang in lng_all_names:

        if lang in lng_common_words:
            continue

        pos = slow.find(lang)

        if pos != -1:
            end = pos + len(lang)
            # make sure our word is always surrounded by separators
            if slow[pos - 1] not in sep or slow[end] not in sep:
                continue

            language = Language(slow[pos:end])
            if lang_filter and language not in lang_filter:
                continue

            # only allow those languages that have a 2-letter code, those who
            # don't are too esoteric and probably false matches
            if language.lang not in lng3_to_lng2:
                continue

            # confidence depends on lng2, lng3, english name, ...
            if len(lang) == 2:
                confidence = 0.8
            elif len(lang) == 3:
                confidence = 0.9
            else:
                # Note: we could either be really confident that we found a
                #       language or assume that full language names are too
                # common words
                confidence = 0.3 # going with the low-confidence route here

            return language, (pos - 1, end - 1), confidence

    return None, None, None
