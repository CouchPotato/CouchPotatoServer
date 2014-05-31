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

from caper.helpers import is_list_type, update_dict, delta_seconds
from datetime import datetime
from logr import Logr
import re


class FragmentMatcher(object):
    def __init__(self, pattern_groups):
        self.regex = {}

        self.construct_patterns(pattern_groups)

    def construct_patterns(self, pattern_groups):
        compile_start = datetime.now()
        compile_count = 0

        for group_name, patterns in pattern_groups:
            if group_name not in self.regex:
                self.regex[group_name] = []

            # Transform into weight groups
            if type(patterns[0]) is str or type(patterns[0][0]) not in [int, float]:
                patterns = [(1.0, patterns)]

            for weight, patterns in patterns:
                weight_patterns = []

                for pattern in patterns:
                    # Transform into multi-fragment patterns
                    if type(pattern) is str:
                        pattern = (pattern,)

                    if type(pattern) is tuple and len(pattern) == 2:
                        if type(pattern[0]) is str and is_list_type(pattern[1], str):
                            pattern = (pattern,)

                    result = []
                    for value in pattern:
                        if type(value) is tuple:
                            if len(value) == 2:
                                # Construct OR-list pattern
                                value = value[0] % '|'.join(value[1])
                            elif len(value) == 1:
                                value = value[0]

                        result.append(re.compile(value, re.IGNORECASE))
                        compile_count += 1

                    weight_patterns.append(tuple(result))

                self.regex[group_name].append((weight, weight_patterns))

        Logr.info("Compiled %s patterns in %ss", compile_count, delta_seconds(datetime.now() - compile_start))

    def find_group(self, name):
        for group_name, weight_groups in self.regex.items():
            if group_name and group_name == name:
                return group_name, weight_groups

        return None, None

    def value_match(self, value, group_name=None, single=True):
        result = None

        for group, weight_groups in self.regex.items():
            if group_name and group != group_name:
                continue

            # TODO handle multiple weights
            weight, patterns = weight_groups[0]

            for pattern in patterns:
                match = pattern[0].match(value)
                if not match:
                    continue

                if result is None:
                    result = {}
                if group not in result:
                    result[group] = {}

                result[group].update(match.groupdict())

                if single:
                    return result

        return result

    def fragment_match(self, fragment, group_name=None):
        """Follow a fragment chain to try find a match

        :type fragment: caper.objects.CaperFragment
        :type group_name: str or None

        :return: The weight of the match found between 0.0 and 1.0,
                  where 1.0 means perfect match and 0.0 means no match
        :rtype: (float, dict, int)
        """

        group_name, weight_groups = self.find_group(group_name)

        for weight, patterns in weight_groups:
            for pattern in patterns:
                cur_fragment = fragment
                success = True
                result = {}

                # Ignore empty patterns
                if len(pattern) < 1:
                    break

                for fragment_pattern in pattern:
                    if not cur_fragment:
                        success = False
                        break

                    match = fragment_pattern.match(cur_fragment.value)
                    if match:
                        update_dict(result, match.groupdict())
                    else:
                        success = False
                        break

                    cur_fragment = cur_fragment.right if cur_fragment else None

                if success:
                    Logr.debug("Found match with weight %s" % weight)
                    return float(weight), result, len(pattern)

        return 0.0, None, 1
