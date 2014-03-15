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

import re
from caper.parsers.base import Parser


REGEX_GROUP = re.compile(r'(\(|\[)(?P<group>.*?)(\)|\])', re.IGNORECASE)


PATTERN_GROUPS = [
    ('identifier', [
        r'S(?P<season>\d+)E(?P<episode>\d+)',
        r'(S(?P<season>\d+))|(E(?P<episode>\d+))',

        r'Ep(?P<episode>\d+)',
        r'$(?P<absolute>\d+)^',

        (r'Episode', r'(?P<episode>\d+)'),
    ]),
    ('video', [
        (r'(?P<h264_profile>%s)', [
            'Hi10P'
        ]),
        (r'.(?P<resolution>%s)', [
            '720p',
            '1080p',

            '960x720',
            '1920x1080'
        ]),
        (r'(?P<source>%s)', [
            'BD'
        ]),
    ]),
    ('audio', [
        (r'(?P<codec>%s)', [
            'FLAC'
        ]),
    ])
]


class AnimeParser(Parser):
    def __init__(self, debug=False):
        super(AnimeParser, self).__init__(PATTERN_GROUPS, debug)

    def capture_group(self, fragment):
        match = REGEX_GROUP.match(fragment.value)

        if not match:
            return None

        return match.group('group')

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.setup(closures)

        self.capture_closure('group', func=self.capture_group)\
            .execute(once=True)

        self.capture_fragment('show_name', single=False)\
            .until_fragment(value__re='identifier')\
            .until_fragment(value__re='video')\
            .execute()

        self.capture_fragment('identifier', regex='identifier') \
            .capture_fragment('video', regex='video', single=False) \
            .capture_fragment('audio', regex='audio', single=False) \
            .execute()

        self.result.build()
        return self.result
