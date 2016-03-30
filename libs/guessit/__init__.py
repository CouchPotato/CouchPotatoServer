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

from __future__ import unicode_literals

__version__ = '0.6.2'
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
from guessit.textutils import clean_string
import logging
import json

log = logging.getLogger(__name__)



class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# let's be a nicely behaving library
h = NullHandler()
log.addHandler(h)


def _guess_filename(filename, filetype):
    def find_nodes(tree, props):
        """Yields all nodes containing any of the given props."""
        if isinstance(props, base_text_type):
            props = [props]
        for node in tree.nodes():
            if any(prop in node.guess for prop in props):
                yield node

    def warning(title):
        log.warning('%s, guesses: %s - %s' % (title, m.nice_string(), m2.nice_string()))
        return m

    mtree = IterativeMatcher(filename, filetype=filetype)

    m = mtree.matched()

    second_pass_opts = []
    second_pass_transfo_opts = {}

    # if there are multiple possible years found, we assume the first one is
    # part of the title, reparse the tree taking this into account
    years = set(n.value for n in find_nodes(mtree.match_tree, 'year'))
    if len(years) >= 2:
        second_pass_opts.append('skip_first_year')

    to_skip_language_nodes = []

    title_nodes = set(n for n in find_nodes(mtree.match_tree, ['title', 'series']))
    title_spans = {}
    for title_node in title_nodes:
        title_spans[title_node.span[0]] = title_node
        title_spans[title_node.span[1]] = title_node

    for lang_key in ('language', 'subtitleLanguage'):
        langs = {}
        lang_nodes = set(n for n in find_nodes(mtree.match_tree, lang_key))

        for lang_node in lang_nodes:
            lang = lang_node.guess.get(lang_key, None)
            if len(lang_node.value) > 3 and (lang_node.span[0] in title_spans.keys() or lang_node.span[1] in title_spans.keys()):
                # Language is next or before title, and is not a language code. Add to skip for 2nd pass.

                # if filetype is subtitle and the language appears last, just before
                # the extension, then it is likely a subtitle language
                parts = clean_string(lang_node.root.value).split()
                if m['type'] in ['moviesubtitle', 'episodesubtitle'] and (parts.index(lang_node.value) == len(parts) - 2):
                    continue

                to_skip_language_nodes.append(lang_node)
            elif not lang in langs:
                langs[lang] = lang_node
            else:
                # The same language was found. Keep the more confident one, and add others to skip for 2nd pass.
                existing_lang_node = langs[lang]
                to_skip = None
                if existing_lang_node.guess.confidence('language') >= lang_node.guess.confidence('language'):
                    # lang_node is to remove
                    to_skip = lang_node
                else:
                    # existing_lang_node is to remove
                    langs[lang] = lang_node
                    to_skip = existing_lang_node
                to_skip_language_nodes.append(to_skip)


    if to_skip_language_nodes:
        second_pass_transfo_opts['guess_language'] = (
            ((), { 'skip': [ { 'node_idx': node.parent.node_idx,
                               'span': node.span }
                             for node in to_skip_language_nodes ] }))

    if second_pass_opts or second_pass_transfo_opts:
        # 2nd pass is needed
        log.info("Running 2nd pass with options: %s" % second_pass_opts)
        log.info("Transfo options: %s" % second_pass_transfo_opts)
        mtree = IterativeMatcher(filename, filetype=filetype,
                                 opts=second_pass_opts,
                                 transfo_opts=second_pass_transfo_opts)

    m = mtree.matched()

    if 'language' not in m and 'subtitleLanguage' not in m or 'title' not in m:
        return m

    # if we found some language, make sure we didn't cut a title or sth...
    mtree2 = IterativeMatcher(filename, filetype=filetype,
                              opts=['nolanguage', 'nocountry'])
    m2 = mtree2.matched()

    if m.get('title') != m2.get('title'):
        title = next(find_nodes(mtree.match_tree, 'title'))
        title2 = next(find_nodes(mtree2.match_tree, 'title'))

        # if a node is in an explicit group, then the correct title is probably
        # the other one
        if title.root.node_at(title.node_idx[:2]).is_explicit():
            return m2
        elif title2.root.node_at(title2.node_idx[:2]).is_explicit():
            return m

    return m


def guess_file_info(filename, filetype, info=None):
    """info can contain the names of the various plugins, such as 'filename' to
    detect filename info, or 'hash_md5' to get the md5 hash of the file.

    >>> guess_file_info('tests/dummy.srt', 'autodetect', info = ['hash_md5', 'hash_sha1'])
    {'hash_md5': 'e781de9b94ba2753a8e2945b2c0a123d', 'hash_sha1': 'bfd18e2f4e5d59775c2bc14d80f56971891ed620'}
    """
    result = []
    hashers = []

    # Force unicode as soon as possible
    filename = u(filename)

    if info is None:
        info = ['filename']

    if isinstance(info, base_text_type):
        info = [info]

    for infotype in info:
        if infotype == 'filename':
            result.append(_guess_filename(filename, filetype))

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
    if 'series' in result and 'country' in result:
        result['series'] += ' (%s)' % result['country'].alpha2.upper()


    return result


def guess_video_info(filename, info=None):
    return guess_file_info(filename, 'autodetect', info)


def guess_movie_info(filename, info=None):
    return guess_file_info(filename, 'movie', info)


def guess_episode_info(filename, info=None):
    return guess_file_info(filename, 'episode', info)
