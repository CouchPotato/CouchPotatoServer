#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
# Copyright (c) 2011 Ricard Marxer <ricardmp@gmail.com>
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
import re


subtitle_exts = [ 'srt', 'idx', 'sub', 'ssa' ]

info_exts = [ 'nfo' ]

video_exts = ['3g2', '3gp', '3gp2', 'asf', 'avi', 'divx', 'flv', 'm4v', 'mk2',
              'mka', 'mkv', 'mov', 'mp4', 'mp4a', 'mpeg', 'mpg', 'ogg', 'ogm',
              'ogv', 'qt', 'ra', 'ram', 'rm', 'ts', 'wav', 'webm', 'wma', 'wmv']

group_delimiters = [ '()', '[]', '{}' ]

# separator character regexp
sep = r'[][,)(}{+ /\._-]' # regexp art, hehe :D

# character used to represent a deleted char (when matching groups)
deleted = '_'

# format: [ (regexp, confidence, span_adjust) ]
episode_rexps = [ # ... Season 2 ...
                  (r'season (?P<season>[0-9]+)', 1.0, (0, 0)),
                  (r'saison (?P<season>[0-9]+)', 1.0, (0, 0)),

                  # ... s02e13 ...
                  (r'[Ss](?P<season>[0-9]{1,3})[^0-9]?(?P<episodeNumber>(?:-?[eE-][0-9]{1,3})+)[^0-9]', 1.0, (0, -1)),

                  # ... s03-x02 ... # FIXME: redundant? remove it?
                  #(r'[Ss](?P<season>[0-9]{1,3})[^0-9]?(?P<bonusNumber>(?:-?[xX-][0-9]{1,3})+)[^0-9]', 1.0, (0, -1)),

                  # ... 2x13 ...
                  (r'[^0-9](?P<season>[0-9]{1,2})[^0-9 .-]?(?P<episodeNumber>(?:-?[xX][0-9]{1,3})+)[^0-9]', 1.0, (1, -1)),

                  # ... s02 ...
                  #(sep + r's(?P<season>[0-9]{1,2})' + sep, 0.6, (1, -1)),
                  (r's(?P<season>[0-9]{1,2})[^0-9]', 0.6, (0, -1)),

                  # v2 or v3 for some mangas which have multiples rips
                  (r'(?P<episodeNumber>[0-9]{1,3})v[23]' + sep, 0.6, (0, 0)),

                  # ... ep 23 ...
                  ('ep' + sep + r'(?P<episodeNumber>[0-9]{1,2})[^0-9]', 0.7, (0, -1)),

                  # ... e13 ... for a mini-series without a season number
                  (sep + r'e(?P<episodeNumber>[0-9]{1,2})' + sep, 0.6, (1, -1))

                  ]


weak_episode_rexps = [ # ... 213 or 0106 ...
                       (sep + r'(?P<episodeNumber>[0-9]{2,4})' + sep, (1, -1))
                       ]

non_episode_title = [ 'extras', 'rip' ]


video_rexps = [ # cd number
                (r'cd ?(?P<cdNumber>[0-9])( ?of ?(?P<cdNumberTotal>[0-9]))?', 1.0, (0, 0)),
                (r'(?P<cdNumberTotal>[1-9]) cds?', 0.9, (0, 0)),

                # special editions
                (r'edition' + sep + r'(?P<edition>collector)', 1.0, (0, 0)),
                (r'(?P<edition>collector)' + sep + 'edition', 1.0, (0, 0)),
                (r'(?P<edition>special)' + sep + 'edition', 1.0, (0, 0)),
                (r'(?P<edition>criterion)' + sep + 'edition', 1.0, (0, 0)),

                # director's cut
                (r"(?P<edition>director'?s?" + sep + "cut)", 1.0, (0, 0)),

                # video size
                (r'(?P<width>[0-9]{3,4})x(?P<height>[0-9]{3,4})', 0.9, (0, 0)),

                # website
                (r'(?P<website>www(\.[a-zA-Z0-9]+){2,3})', 0.8, (0, 0)),

                # bonusNumber: ... x01 ...
                (r'x(?P<bonusNumber>[0-9]{1,2})', 1.0, (0, 0)),

                # filmNumber: ... f01 ...
                (r'f(?P<filmNumber>[0-9]{1,2})', 1.0, (0, 0))
                ]

websites = [ 'tvu.org.ru', 'emule-island.com', 'UsaBit.com', 'www.divx-overnet.com',
             'sharethefiles.com' ]

unlikely_series = [ 'series' ]


# prop_multi is a dict of { property_name: { canonical_form: [ pattern ] } }
# pattern is a string considered as a regexp, with the addition that dashes are
# replaced with '([ \.-_])?' which matches more types of separators (or none)
# note: simpler patterns need to be at the end of the list to not shadow more
#       complete ones, eg: 'AAC' needs to come after 'He-AAC'
#       ie: from most specific to less specific
prop_multi = { 'format': { 'DVD': [ 'DVD', 'DVD-Rip', 'VIDEO-TS', 'DVDivX' ],
                           'HD-DVD': [ 'HD-(?:DVD)?-Rip', 'HD-DVD' ],
                           'BluRay': [ 'Blu-ray', 'B[DR]Rip' ],
                           'HDTV': [ 'HD-TV' ],
                           'DVB': [ 'DVB-Rip', 'DVB', 'PD-TV' ],
                           'WEBRip': [ 'WEB-Rip' ],
                           'Screener': [ 'DVD-SCR', 'Screener' ],
                           'VHS': [ 'VHS' ],
                           'WEB-DL': [ 'WEB-DL' ] },

               'is3D': { True: [ '3D' ] },

               'screenSize': { '480p': [ '480[pi]?' ],
                               '720p': [ '720[pi]?' ],
                               '1080i': [ '1080i' ],
                               '1080p': [ '1080p', '1080[^i]' ] },

               'videoCodec': { 'XviD': [ 'Xvid' ],
                               'DivX': [ 'DVDivX', 'DivX' ],
                               'h264': [ '[hx]-264' ],
                               'Rv10': [ 'Rv10' ],
                               'Mpeg2': [ 'Mpeg2' ] },

               # has nothing to do here (or on filenames for that matter), but some
               # releases use it and it helps to identify release groups, so we adapt
               'videoApi': {  'DXVA': [ 'DXVA' ] },

               'audioCodec': { 'AC3': [ 'AC3' ],
                               'DTS': [ 'DTS' ],
                               'AAC': [ 'He-AAC', 'AAC-He', 'AAC' ] },

               'audioChannels': { '5.1': [ r'5\.1', 'DD5[._ ]1', '5ch' ] },

               'episodeFormat': { 'Minisode': [ 'Minisodes?' ] }

               }

# prop_single dict of { property_name: [ canonical_form ] }
prop_single = { 'releaseGroup': [ 'ESiR', 'WAF', 'SEPTiC', r'\[XCT\]', 'iNT', 'PUKKA',
                                  'CHD', 'ViTE', 'TLF', 'FLAiTE',
                                  'MDX', 'GM4F', 'DVL', 'SVD', 'iLUMiNADOS',
                                  'aXXo', 'KLAXXON', 'NoTV', 'ZeaL', 'LOL',
                                  'CtrlHD', 'POD', 'WiKi','IMMERSE', 'FQM',
                                  '2HD',  'CTU', 'HALCYON', 'EbP', 'SiTV',
                                  'HDBRiSe', 'AlFleNi-TeaM', 'EVOLVE', '0TV',
                                  'TLA', 'NTB', 'ASAP', 'MOMENTUM', 'FoV', 'D-Z0N3',
                                  'TrollHD', 'ECI'
                                  ],

                # potentially confusing release group names (they are words)
                'weakReleaseGroup': [ 'DEiTY', 'FiNaLe', 'UnSeeN', 'KiNGS', 'CLUE', 'DIMENSION',
                                      'SAiNTS', 'ARROW', 'EuReKA', 'SiNNERS', 'DiRTY', 'REWARD',
                                      'REPTiLE',
                                      ],

                'other': [ 'PROPER', 'REPACK', 'LIMITED', 'DualAudio', 'Audiofixed', 'R5',
                           'complete', 'classic', # not so sure about these ones, could appear in a title
                           'ws' ] # widescreen
                }

_dash = '-'
_psep = '[-. _]?'

def _to_rexp(prop):
    return re.compile(prop.replace(_dash, _psep), re.IGNORECASE)

# properties_rexps dict of { property_name: { canonical_form: [ rexp ] } }
# containing the rexps compiled from both prop_multi and prop_single
properties_rexps = dict((type, dict((canonical_form,
                                     [ _to_rexp(pattern) for pattern in patterns ])
                                    for canonical_form, patterns in props.items()))
                        for type, props in prop_multi.items())

properties_rexps.update(dict((type, dict((canonical_form, [ _to_rexp(canonical_form) ])
                                         for canonical_form in props))
                             for type, props in prop_single.items()))



def find_properties(string):
    result = []
    for property_name, props in properties_rexps.items():
        # FIXME: this should be done in a more flexible way...
        if property_name in ['weakReleaseGroup']:
            continue

        for canonical_form, rexps in props.items():
            for value_rexp in rexps:
                match = value_rexp.search(string)
                if match:
                    start, end = match.span()
                    # make sure our word is always surrounded by separators
                    # note: sep is a regexp, but in this case using it as
                    #       a char sequence achieves the same goal
                    if ((start > 0 and string[start-1] not in sep) or
                        (end < len(string) and string[end] not in sep)):
                        continue

                    result.append((property_name, canonical_form, start, end))
    return result


property_synonyms = { 'Special Edition': [ 'Special' ],
                      'Collector Edition': [ 'Collector' ],
                      'Criterion Edition': [ 'Criterion' ]
                      }


def revert_synonyms():
    reverse = {}

    for canonical, synonyms in property_synonyms.items():
        for synonym in synonyms:
            reverse[synonym.lower()] = canonical

    return reverse


reverse_synonyms = revert_synonyms()


def canonical_form(string):
    return reverse_synonyms.get(string.lower(), string)


def compute_canonical_form(property_name, value):
    """Return the canonical form of a property given its type if it is a valid
    one, None otherwise."""
    if isinstance(value, basestring):
        for canonical_form, rexps in properties_rexps[property_name].items():
            for rexp in rexps:
                if rexp.match(value):
                    return canonical_form
    return None
