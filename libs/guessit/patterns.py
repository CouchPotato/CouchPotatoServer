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


subtitle_exts = [ 'srt', 'idx', 'sub', 'ssa', 'txt' ]

video_exts = ['3g2', '3gp', '3gp2', 'asf', 'avi', 'divx', 'flv', 'm4v', 'mk2',
              'mka', 'mkv', 'mov', 'mp4', 'mp4a', 'mpeg', 'mpg', 'ogg', 'ogm',
              'ogv', 'qt', 'ra', 'ram', 'rm', 'ts', 'wav', 'webm', 'wma', 'wmv']

group_delimiters = [ '()', '[]', '{}' ]

# separator character regexp
sep = r'[][)(}{+ /\._-]' # regexp art, hehe :D

# character used to represent a deleted char (when matching groups)
deleted = '_'

# format: [ (regexp, confidence, span_adjust) ]
episode_rexps = [ # ... Season 2 ...
                  (r'season (?P<season>[0-9]+)', 1.0, (0, 0)),
                  (r'saison (?P<season>[0-9]+)', 1.0, (0, 0)),

                  # ... s02e13 ...
                  (r'[Ss](?P<season>[0-9]{1,2}).{,3}(?P<episodeNumber>(?:[EeXx][0-9]{1,2})+)[^0-9]', 1.0, (0, -1)),

                  # ... 2x13 ...
                  (r'[^0-9](?P<season>[0-9]{1,2})(?P<episodeNumber>(?:[xX][0-9]{1,2})+)[^0-9]', 0.8, (1, -1)),

                  # ... s02 ...
                  #(sep + r's(?P<season>[0-9]{1,2})' + sep, 0.6, (1, -1)),
                  (r's(?P<season>[0-9]{1,2})[^0-9]', 0.6, (0, -1)),

                  # v2 or v3 for some mangas which have multiples rips
                  (r'(?P<episodeNumber>[0-9]{1,3})v[23]' + sep, 0.6, (0, 0)),

                  # ... ep 23 ...
                  ('ep' + sep + r'(?P<episodeNumber>[0-9]{1,2})[^0-9]', 0.7, (0, -1))
                  ]


weak_episode_rexps = [ # ... 213 or 0106 ...
                       (sep + r'(?P<episodeNumber>[0-9]{1,4})' + sep, (1, -1)),

                       # ... 2x13 ...
                       (sep + r'[^0-9](?P<season>[0-9]{1,2})\.(?P<episodeNumber>[0-9]{1,2})[^0-9]' + sep, (1, -1)),

                       # ... e13 ... for a mini-series without a season number
                       (r'e(?P<episodeNumber>[0-9]{1,4})[^0-9]', (0, -1)),
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

websites = [ 'tvu.org.ru', 'emule-island.com', 'UsaBit.com', 'www.divx-overnet.com', 'sharethefiles.com' ]

unlikely_series = ['series']

properties = { 'format': [ 'DVDRip', 'HD-DVD', 'HDDVD', 'HDDVDRip', 'BluRay', 'Blu-ray', 'BDRip', 'BRRip',
                           'HDRip', 'DVD', 'DVDivX', 'HDTV', 'DVB', 'DVBRip', 'PDTV', 'WEBRip',
                           'DVDSCR', 'Screener', 'VHS', 'VIDEO_TS' ],

               'screenSize': [ '720p', '720', '1080p', '1080' ],

               'videoCodec': [ 'XviD', 'DivX', 'x264', 'h264', 'Rv10' ],

               'audioCodec': [ 'AC3', 'DTS', 'He-AAC', 'AAC-He', 'AAC' ],

               'audioChannels': [ '5.1' ],

               'releaseGroup': [ 'ESiR', 'WAF', 'SEPTiC', '[XCT]', 'iNT', 'PUKKA',
                                 'CHD', 'ViTE', 'TLF', 'DEiTY', 'FLAiTE',
                                 'MDX', 'GM4F', 'DVL', 'SVD', 'iLUMiNADOS', ' FiNaLe',
                                 'UnSeeN', 'aXXo', 'KLAXXON', 'NoTV', 'ZeaL', 'LOL',
                                 'HDBRiSe' ],

               'episodeFormat': [ 'Minisode', 'Minisodes' ],

               'other': [ '5ch', 'PROPER', 'REPACK', 'LIMITED', 'DualAudio', 'iNTERNAL', 'Audiofixed', 'R5',
                          'complete', 'classic', # not so sure about these ones, could appear in a title
                          'ws', # widescreen
                          ],
               }


def find_properties(filename):
    result = []
    clow = filename.lower()
    for prop, values in properties.items():
        for value in values:
            pos = clow.find(value.lower())
            if pos != -1:
                end = pos + len(value)
                # make sure our word is always surrounded by separators
                if ((pos > 0 and clow[pos - 1] not in sep) or
                    (end < len(clow) and clow[end] not in sep)):
                    # note: sep is a regexp, but in this case using it as
                    #       a sequence achieves the same goal
                    continue

                result.append((prop, value, pos, end))
    return result


property_synonyms = { 'DVD': [ 'DVDRip', 'VIDEO_TS' ],
                      'HD-DVD': [ 'HDDVD', 'HDDVDRip' ],
                      'BluRay': [ 'BDRip', 'BRRip', 'Blu-ray' ],
                      'DVB': [ 'DVBRip', 'PDTV' ],
                      'Screener': [ 'DVDSCR' ],
                      'DivX': [ 'DVDivX' ],
                      'h264': [ 'x264' ],
                      '720p': [ '720' ],
                      '1080p': [ '1080' ],
                      'AAC': [ 'He-AAC', 'AAC-He' ],
                      'Special Edition': [ 'Special' ],
                      'Collector Edition': [ 'Collector' ],
                      'Criterion Edition': [ 'Criterion' ],
                      'Minisode': [ 'Minisodes' ]
                      }


def revert_synonyms():
    reverse = {}

    for _, values in properties.items():
        for value in values:
            reverse[value.lower()] = value

    for canonical, synonyms in property_synonyms.items():
        for synonym in synonyms:
            reverse[synonym.lower()] = canonical

    return reverse

reverse_synonyms = revert_synonyms()


def canonical_form(string):
    return reverse_synonyms.get(string.lower(), string)
