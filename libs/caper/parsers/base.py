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

from caper import FragmentMatcher
from caper.group import CaptureGroup
from caper.result import CaperResult, CaperClosureNode, CaperRootNode
from logr import Logr


class Parser(object):
    def __init__(self, matcher, debug=False):
        self.debug = debug

        self.matcher = matcher

        self.closures = None
        #: :type: caper.result.CaperResult
        self.result = None

        self._match_cache = None
        self._fragment_pos = None
        self._closure_pos = None
        self._history = None

        self.reset()

    def reset(self):
        self.closures = None
        self.result = CaperResult()

        self._match_cache = {}
        self._fragment_pos = -1
        self._closure_pos = -1
        self._history = []

    def setup(self, closures):
        """
        :type closures: list of CaperClosure
        """

        self.reset()
        self.closures = closures

        self.result.heads = [CaperRootNode(closures[0])]

    def run(self, closures):
        """
        :type closures: list of CaperClosure
        """

        raise NotImplementedError()

    #
    # Capture Methods
    #

    def capture_fragment(self, tag, regex=None, func=None, single=True, **kwargs):
        return CaptureGroup(self, self.result).capture_fragment(
            tag,
            regex=regex,
            func=func,
            single=single,
            **kwargs
        )

    def capture_closure(self, tag, regex=None, func=None, single=True, **kwargs):
        return CaptureGroup(self, self.result).capture_closure(
            tag,
            regex=regex,
            func=func,
            single=single,
            **kwargs
        )
