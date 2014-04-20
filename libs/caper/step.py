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

from caper.objects import CaptureMatch
from logr import Logr


class CaptureStep(object):
    REPR_KEYS = ['regex', 'func', 'single']

    def __init__(self, capture_group, tag, source, regex=None, func=None, single=None, **kwargs):
        #: @type: CaptureGroup
        self.capture_group = capture_group

        #: @type: str
        self.tag = tag
        #: @type: str
        self.source = source
        #: @type: str
        self.regex = regex
        #: @type: function
        self.func = func
        #: @type: bool
        self.single = single

        self.kwargs = kwargs

        self.matched = False

    def execute(self, fragment):
        """Execute step on fragment

        :type fragment: CaperFragment
        :rtype : CaptureMatch
        """

        match = CaptureMatch(self.tag, self)

        if self.regex:
            weight, result, num_fragments = self.capture_group.parser.matcher.fragment_match(fragment, self.regex)
            Logr.debug('(execute) [regex] tag: "%s"', self.tag)

            if not result:
                return match

            # Populate CaptureMatch
            match.success = True
            match.weight = weight
            match.result = result
            match.num_fragments = num_fragments
        elif self.func:
            result = self.func(fragment)
            Logr.debug('(execute) [func] %s += "%s"', self.tag, match)

            if not result:
                return match

            # Populate CaptureMatch
            match.success = True
            match.weight = 1.0
            match.result = result
        else:
            Logr.debug('(execute) [raw] %s += "%s"', self.tag, fragment.value)

            include_separators = self.kwargs.get('include_separators', False)

            # Populate CaptureMatch
            match.success = True
            match.weight = 1.0

            if include_separators:
                match.result = (fragment.left_sep, fragment.value, fragment.right_sep)
            else:
                match.result = fragment.value

        return match

    def __repr__(self):
        attribute_values = [key + '=' + repr(getattr(self, key))
                            for key in self.REPR_KEYS
                            if hasattr(self, key) and getattr(self, key)]

        attribute_string = ', ' + ', '.join(attribute_values) if len(attribute_values) > 0 else ''

        return "CaptureStep('%s'%s)" % (self.tag, attribute_string)
