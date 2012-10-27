# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
import re


__all__ = ['get_keywords', 'split_keyword', 'to_unicode']


def get_keywords(guess):
    """Retrieve keywords from guessed informations

    :param guess: guessed informations
    :type guess: :class:`guessit.guess.Guess`
    :return: lower case alphanumeric keywords
    :rtype: set

    """
    keywords = set()
    for k in ['releaseGroup', 'screenSize', 'videoCodec', 'format']:
        if k in guess:
            keywords = keywords | split_keyword(guess[k].lower())
    return keywords


def split_keyword(keyword):
    """Split a keyword in multiple ones on any non-alphanumeric character

    :param string keyword: keyword
    :return: keywords
    :rtype: set

    """
    split = set(re.findall(r'\w+', keyword))
    return split


def to_unicode(data):
    """Convert a basestring to unicode

    :param basestring data: data to decode
    :return: data as unicode
    :rtype: unicode

    """
    if not isinstance(data, basestring):
        raise ValueError('Basestring expected')
    if isinstance(data, unicode):
        return data
    for encoding in ('utf-8', 'latin-1'):
        try:
            return unicode(data, encoding)
        except UnicodeDecodeError:
            pass
    return unicode(data, 'utf-8', 'replace')
