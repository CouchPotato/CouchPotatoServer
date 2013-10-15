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


from difflib import SequenceMatcher
import re
import sys
from logr import Logr
from qcond.compat import xrange


PY3 = sys.version_info[0] == 3


def simplify(s):
    s = s.lower()
    s = re.sub(r"(\w)'(\w)", r"\1\2", s)
    return s


def strip(s):
    return re.sub(r"^(\W*)(.*?)(\W*)$", r"\2", s)


def create_matcher(a, b, swap_longest = True, case_sensitive = False):
    # Ensure longest string is a
    if swap_longest and len(b) > len(a):
        a_ = a
        a = b
        b = a_

    if not case_sensitive:
        a = a.upper()
        b = b.upper()

    return SequenceMatcher(None, a, b)


def first(function_or_none, sequence):
    if PY3:
        for item in filter(function_or_none, sequence):
            return item
    else:
        result = filter(function_or_none, sequence)
        if len(result):
            return result[0]

    return None

def sorted_append(sequence, item, func):
    if not len(sequence):
        sequence.insert(0, item)
        return

    x = 0
    for x in xrange(len(sequence)):
        if func(sequence[x]):
            sequence.insert(x, item)
            return

    sequence.append(item)

def itemsMatch(L1, L2):
    return len(L1) == len(L2) and sorted(L1) == sorted(L2)

def distinct(sequence):
    result = []

    for item in sequence:
        if item not in result:
            result.append(item)

    return result