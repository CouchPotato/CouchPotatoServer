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


__version__ = '0.5.2'
__all__ = ['Guess', 'Language',
           'guess_file_info', 'guess_video_info',
           'guess_movie_info', 'guess_episode_info']


# Do python3 detection before importing any other module, to be sure that
# it will then always be available
# with code from http://lucumr.pocoo.org/2011/1/22/forwards-compatible-python/
import sys
if sys.version_info[0] >= 3:
    PY3 = True
    unicode_text_type = str
    native_text_type = str
    base_text_type = str
    def u(x):
        return str(x)
    def s(x):
        return x
    class UnicodeMixin(object):
        __str__ = lambda x: x.__unicode__()
    import binascii
    def to_hex(x):
        return binascii.hexlify(x).decode('utf-8')

else:
    PY3 = False
    __all__ = [ str(s) for s in __all__ ] # fix imports for python2
    unicode_text_type = unicode
    native_text_type = str
    base_text_type = basestring
    def u(x):
        if isinstance(x, str):
            return x.decode('utf-8')
        return unicode(x)
    def s(x):
        if isinstance(x, unicode):
            return x.encode('utf-8')
        if isinstance(x, list):
            return [ s(y) for y in x ]
        if isinstance(x, tuple):
            return tuple(s(y) for y in x)
        if isinstance(x, dict):
            return dict((s(key), s(value)) for key, value in x.items())
        return x
    class UnicodeMixin(object):
        __str__ = lambda x: unicode(x).encode('utf-8')
    def to_hex(x):
        return x.encode('hex')


from guessit.guess import Guess, merge_all
from guessit.language import Language
from guessit.matcher import IterativeMatcher
import logging

log = logging.getLogger(__name__)



class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# let's be a nicely behaving library
h = NullHandler()
log.addHandler(h)


def guess_file_info(filename, filetype, info=None):
    """info can contain the names of the various plugins, such as 'filename' to
    detect filename info, or 'hash_md5' to get the md5 hash of the file.

    >>> guess_file_info('tests/dummy.srt', 'autodetect', info = ['hash_md5', 'hash_sha1'])
    {'hash_md5': 'e781de9b94ba2753a8e2945b2c0a123d', 'hash_sha1': 'bfd18e2f4e5d59775c2bc14d80f56971891ed620'}
    """
    result = []
    hashers = []

    if info is None:
        info = ['filename']

    if isinstance(info, base_text_type):
        info = [info]

    for infotype in info:
        if infotype == 'filename':
            m = IterativeMatcher(filename, filetype=filetype)
            result.append(m.matched())

        elif infotype == 'hash_mpc':
            from guessit.hash_mpc import hash_file
            try:
                result.append(Guess({'hash_mpc': hash_file(filename)},
                                    confidence=1.0))
            except Exception as e:
                log.warning('Could not compute MPC-style hash because: %s' % e)

        elif infotype == 'hash_ed2k':
            from guessit.hash_ed2k import hash_file
            try:
                result.append(Guess({'hash_ed2k': hash_file(filename)},
                                    confidence=1.0))
            except Exception as e:
                log.warning('Could not compute ed2k hash because: %s' % e)

        elif infotype.startswith('hash_'):
            import hashlib
            hashname = infotype[5:]
            try:
                hasher = getattr(hashlib, hashname)()
                hashers.append((infotype, hasher))
            except AttributeError:
                log.warning('Could not compute %s hash because it is not available from python\'s hashlib module' % hashname)

        else:
            log.warning('Invalid infotype: %s' % infotype)

    # do all the hashes now, but on a single pass
    if hashers:
        try:
            blocksize = 8192
            hasherobjs = dict(hashers).values()

            with open(filename, 'rb') as f:
                chunk = f.read(blocksize)
                while chunk:
                    for hasher in hasherobjs:
                        hasher.update(chunk)
                    chunk = f.read(blocksize)

            for infotype, hasher in hashers:
                result.append(Guess({infotype: hasher.hexdigest()},
                                    confidence=1.0))
        except Exception as e:
            log.warning('Could not compute hash because: %s' % e)

    result = merge_all(result)

    # last minute adjustments

    # if country is in the guessed properties, make it part of the filename
    if 'country' in result:
        result['series'] += ' (%s)' % result['country'].alpha2.upper()


    return result


def guess_video_info(filename, info=None):
    return guess_file_info(filename, 'autodetect', info)


def guess_movie_info(filename, info=None):
    return guess_file_info(filename, 'movie', info)


def guess_episode_info(filename, info=None):
    return guess_file_info(filename, 'episode', info)
