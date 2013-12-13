# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from logr import Logr
from caper import FragmentMatcher
from caper.parsers.base import Parser
from caper.result import CaperFragmentNode


PATTERN_GROUPS = [
    ('identifier', [
        (1.0, [
            # S01E01-E02
            ('^S(?P<season>\d+)E(?P<episode_from>\d+)$', '^E(?P<episode_to>\d+)$'),
            # 'S03 E01 to E08' or 'S03 E01 - E09'
            ('^S(?P<season>\d+)$', '^E(?P<episode_from>\d+)$', '^(to|-)$', '^E(?P<episode_to>\d+)$'),
            # 'E01 to E08' or 'E01 - E09'
            ('^E(?P<episode_from>\d+)$', '^(to|-)$', '^E(?P<episode_to>\d+)$'),

            # S01-S03
            ('^S(?P<season_from>\d+)$', '^S(?P<season_to>\d+)$'),

            # S02E13
            r'^S(?P<season>\d+)E(?P<episode>\d+)$',
            # S01 E13
            (r'^(S(?P<season>\d+))$', r'^(E(?P<episode>\d+))$'),
            # S02
            # E13
            r'^((S(?P<season>\d+))|(E(?P<episode>\d+)))$',
            # 3x19
            r'^(?P<season>\d+)x(?P<episode>\d+)$',

            # 2013.09.15
            (r'^(?P<year>\d{4})$', r'^(?P<month>\d{2})$', r'^(?P<day>\d{2})$'),
            # 09.15.2013
            (r'^(?P<month>\d{2})$', r'^(?P<day>\d{2})$', r'^(?P<year>\d{4})$'),
            # TODO - US/UK Date Format Conflict? will only support US format for now..
            # 15.09.2013
            #(r'^(?P<day>\d{2})$', r'^(?P<month>\d{2})$', r'^(?P<year>\d{4})$'),
            # 130915
            r'^(?P<year_short>\d{2})(?P<month>\d{2})(?P<day>\d{2})$',

            # Season 3 Episode 14
            (r'^Se(ason)?$', r'^(?P<season>\d+)$', r'^Ep(isode)?$', r'^(?P<episode>\d+)$'),
            # Season 3
            (r'^Se(ason)?$', r'^(?P<season>\d+)$'),
            # Episode 14
            (r'^Ep(isode)?$', r'^(?P<episode>\d+)$'),

            # Part.3
            # Part.1.and.Part.3
            ('^Part$', '(?P<part>\d+)'),

            r'(?P<extra>Special)',
            r'(?P<country>NZ|AU|US|UK)'
        ]),
        (0.8, [
            # 100 - 1899, 2100 - 9999 (skips 1900 to 2099 - so we don't get years my mistake)
            # TODO - Update this pattern on 31 Dec 2099
            r'^(?P<season>([1-9])|(1[0-8])|(2[1-9])|([3-9][0-9]))(?P<episode>\d{2})$'
        ]),
        (0.5, [
            # 100 - 9999
            r'^(?P<season>([1-9])|([1-9][0-9]))(?P<episode>\d{2})$'
        ])
    ]),

    ('video', [
        r'(?P<aspect>FS|WS)',

        (r'(?P<resolution>%s)', [
            '480p',
            '720p',
            '1080p'
        ]),

        #
        # Source
        #

        (r'(?P<source>%s)', [
            'DVDRiP',
            # HDTV
            'HDTV',
            'PDTV',
            'DSR',
            # WEB
            'WEBRip',
            'WEBDL',
            # BluRay
            'BluRay',
            'B(D|R)Rip',
            # DVD
            'DVDR',
            'DVD9',
            'DVD5'
        ]),

        # For multi-fragment 'WEB-DL', 'WEB-Rip', etc... matches
        ('(?P<source>WEB)', '(?P<source>DL|Rip)'),

        #
        # Codec
        #

        (r'(?P<codec>%s)', [
            'x264',
            'XViD',
            'H264',
            'AVC'
        ]),

        # For multi-fragment 'H 264' tags
        ('(?P<codec>H)', '(?P<codec>264)'),
    ]),

    ('dvd', [
        r'D(ISC)?(?P<disc>\d+)',

        r'R(?P<region>[0-8])',

        (r'(?P<encoding>%s)', [
            'PAL',
            'NTSC'
        ]),
    ]),

    ('audio', [
        (r'(?P<codec>%s)', [
            'AC3',
            'TrueHD'
        ]),

        (r'(?P<language>%s)', [
            'GERMAN',
            'DUTCH',
            'FRENCH',
            'SWEDiSH',
            'DANiSH',
            'iTALiAN'
        ]),
    ]),

    ('scene', [
        r'(?P<proper>PROPER|REAL)',
    ])
]


class SceneParser(Parser):
    matcher = None

    def __init__(self, debug=False):
        if not SceneParser.matcher:
            SceneParser.matcher = FragmentMatcher(PATTERN_GROUPS)
            Logr.info("Fragment matcher for %s created", self.__class__.__name__)

        super(SceneParser, self).__init__(SceneParser.matcher, debug)

    def capture_group(self, fragment):
        if fragment.closure.index + 1 != len(self.closures):
            return None

        if fragment.left_sep != '-' or fragment.right:
            return None

        return fragment.value

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.setup(closures)

        self.capture_fragment('show_name', single=False)\
            .until_fragment(node__re='identifier')\
            .until_fragment(node__re='video')\
            .until_fragment(node__re='dvd')\
            .until_fragment(node__re='audio')\
            .until_fragment(node__re='scene')\
            .execute()

        self.capture_fragment('identifier', regex='identifier', single=False)\
            .capture_fragment('video', regex='video', single=False)\
            .capture_fragment('dvd', regex='dvd', single=False)\
            .capture_fragment('audio', regex='audio', single=False)\
            .capture_fragment('scene', regex='scene', single=False)\
            .until_fragment(left_sep__eq='-', right__eq=None)\
            .execute()

        self.capture_fragment('group', func=self.capture_group)\
            .execute()

        self.print_tree(self.result.heads)

        self.result.build()
        return self.result

    def print_tree(self, heads):
        if not self.debug:
            return

        for head in heads:
            head = head if type(head) is list else [head]

            if type(head[0]) is CaperFragmentNode:
                for fragment in head[0].fragments:
                    Logr.debug(fragment.value)
            else:
                Logr.debug(head[0].closure.value)

            for node in head:
                Logr.debug('\t' + str(node).ljust(55) + '\t' + (
                    str(node.match.weight) + '\t' + str(node.match.result)
                ) if node.match else '')

            if len(head) > 0 and head[0].parent:
                self.print_tree([head[0].parent])
