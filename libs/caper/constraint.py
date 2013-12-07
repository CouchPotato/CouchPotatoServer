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


class CaptureConstraint(object):
    def __init__(self, capture_group, comparisons=None, **kwargs):
        """Capture constraint object

        :type capture_group: CaptureGroup
        """

        self.capture_group = capture_group

        self.comparisons = comparisons if comparisons else []

        for key, value in kwargs.items():
            key = key.split('__')
            if len(key) != 2:
                continue
            name, method = key

            method = '_compare_' + method
            if not hasattr(self, method):
                continue

            self.comparisons.append((name, getattr(self, method), value))

    def _compare_eq(self, fragment, name, expected):
        if not hasattr(fragment, name):
            return 1.0, False

        return 1.0, getattr(fragment, name) == expected

    def _compare_re(self, fragment, name, arg):
        if name == 'fragment':
            group, minimum_weight = arg if type(arg) is tuple and len(arg) > 1 else (arg, 0)

            weight, match, num_fragments = self.capture_group.parser.matcher.fragment_match(fragment, group)
            return weight, weight > minimum_weight
        elif type(arg).__name__ == 'SRE_Pattern':
            return 1.0, arg.match(getattr(fragment, name)) is not None
        elif hasattr(fragment, name):
            match = self.capture_group.parser.matcher.value_match(getattr(fragment, name), arg, single=True)
            return 1.0, match is not None
        else:
            raise ValueError("Unable to find attribute with name '%s'" % name)

    def execute(self, fragment):
        results = []
        total_weight = 0

        for name, method, argument in self.comparisons:
            weight, success = method(fragment, name, argument)
            total_weight += weight
            results.append(success)

        return total_weight / float(len(results)), all(results) if len(results) > 0 else False

    def __repr__(self):
        return "CaptureConstraint(comparisons=%s)" % repr(self.comparisons)
