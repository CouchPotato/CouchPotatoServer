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

from caper.helpers import xrange_six


class CaperClosure(object):
    __key__ = 'closure'

    def __init__(self, index, value):
        #: :type: int
        self.index = index

        #: :type: str
        self.value = value

        #: :type: CaperClosure
        self.left = None
        #: :type: CaperClosure
        self.right = None

        #: :type: list of CaperFragment
        self.fragments = []

    def __str__(self):
        return "<CaperClosure value: %s" % repr(self.value)

    def __repr__(self):
        return self.__str__()


class CaperFragment(object):
    __key__ = 'fragment'

    def __init__(self, closure=None):
        #: :type: CaperClosure
        self.closure = closure

        #: :type: str
        self.value = ""

        #: :type: CaperFragment
        self.left = None
        #: :type: str
        self.left_sep = None

        #: :type: CaperFragment
        self.right = None
        #: :type: str
        self.right_sep = None

        #: :type: int
        self.position = None

    def take(self, direction, count, include_self=True):
        if direction not in ['left', 'right']:
            raise ValueError('Un-Expected value for "direction", expected "left" or "right".')

        result = []

        if include_self:
            result.append(self)
            count -= 1

        cur = self
        for x in xrange_six(count):
            if cur and getattr(cur, direction):
                cur = getattr(cur, direction)
                result.append(cur)
            else:
                result.append(None)
                cur = None

        return result

    def take_left(self, count, include_self=True):
        return self.take('left', count, include_self)

    def take_right(self, count, include_self=True):
        return self.take('right', count, include_self)

    def __str__(self):
        return "<CaperFragment value: %s" % repr(self.value)

    def __repr__(self):
        return self.__str__()


class CaptureMatch(object):
    def __init__(self, tag, step, success=False, weight=None, result=None, num_fragments=1):
        #: :type: bool
        self.success = success

        #: :type: float
        self.weight = weight

        #: :type: dict or str
        self.result = result

        #: :type: int
        self.num_fragments = num_fragments

        #: :type: str
        self.tag = tag

        #: :type: CaptureStep
        self.step = step

    def __str__(self):
        return "<CaperMatch result: %s>" % repr(self.result)

    def __repr__(self):
        return self.__str__()
