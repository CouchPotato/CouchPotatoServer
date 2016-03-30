#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2012 Nicolas Wack <wackou@gmail.com>
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
from guessit.transfo import SingleNodeGuesser
from guessit.patterns import prop_multi, compute_canonical_form, _dash, _psep
import re
import logging

log = logging.getLogger(__name__)

def get_patterns(property_name):
    return [ p.replace(_dash, _psep) for patterns in prop_multi[property_name].values() for p in patterns  ]

CODECS = get_patterns('videoCodec')
FORMATS = get_patterns('format')
VAPIS = get_patterns('videoApi')

# RG names following a codec or format, with a potential space or dash inside the name
GROUP_NAMES = [ r'(?P<videoCodec>' + codec + r')[ \.-](?P<releaseGroup>.+?([- \.].*?)??)[ \.]'
                for codec in CODECS ]
GROUP_NAMES += [ r'(?P<format>'    + fmt   + r')[ \.-](?P<releaseGroup>.+?([- \.].*?)??)[ \.]'
                 for fmt in FORMATS ]
GROUP_NAMES += [ r'(?P<videoApi>'  + api   + r')[ \.-](?P<releaseGroup>.+?([- \.].*?)??)[ \.]'
                 for api in VAPIS ]

GROUP_NAMES2 = [ r'\.(?P<videoCodec>' + codec + r')-(?P<releaseGroup>.*?)(-(.*?))?[ \.]'
                 for codec in CODECS ]
GROUP_NAMES2 += [ r'\.(?P<format>'    + fmt   + r')-(?P<releaseGroup>.*?)(-(.*?))?[ \.]'
                  for fmt in FORMATS ]
GROUP_NAMES2 += [ r'\.(?P<videoApi>'  + vapi  + r')-(?P<releaseGroup>.*?)(-(.*?))?[ \.]'
                  for vapi in VAPIS ]

GROUP_NAMES = [ re.compile(r, re.IGNORECASE) for r in GROUP_NAMES ]
GROUP_NAMES2 = [ re.compile(r, re.IGNORECASE) for r in GROUP_NAMES2 ]

def adjust_metadata(md):
    return dict((property_name, compute_canonical_form(property_name, value) or value)
                for property_name, value in md.items())


def guess_release_group(string):
    # first try to see whether we have both a known codec and a known release group
    for rexp in GROUP_NAMES:
        match = rexp.search(string)
        while match:
            metadata = match.groupdict()
            # make sure this is an actual release group we caught
            release_group = (compute_canonical_form('releaseGroup', metadata['releaseGroup']) or
                             compute_canonical_form('weakReleaseGroup', metadata['releaseGroup']))
            if release_group:
                return adjust_metadata(metadata), (match.start(1), match.end(2))

            # we didn't find anything conclusive, keep searching
            match = rexp.search(string, match.span()[0]+1)

    # pick anything as releaseGroup as long as we have a codec in front
    # this doesn't include a potential dash ('-') ending the release group
    # eg: [...].X264-HiS@SiLUHD-English.[...]
    for rexp in GROUP_NAMES2:
        match = rexp.search(string)
        if match:
            return adjust_metadata(match.groupdict()), (match.start(1), match.end(2))

    return None, None


def process(mtree):
    SingleNodeGuesser(guess_release_group, 0.8, log).process(mtree)
