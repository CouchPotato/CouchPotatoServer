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
from caper.matcher import FragmentMatcher
from caper.objects import CaperFragment, CaperClosure
from caper.parsers.anime import AnimeParser
from caper.parsers.scene import SceneParser
from caper.parsers.usenet import UsenetParser


__version_info__ = ('0', '3', '1')
__version_branch__ = 'master'

__version__ = "%s%s" % (
    '.'.join(__version_info__),
    '-' + __version_branch__ if __version_branch__ else ''
)


CL_START_CHARS = ['(', '[', '<', '>']
CL_END_CHARS = [')', ']', '<', '>']
CL_END_STRINGS = [' - ']

STRIP_START_CHARS = ''.join(CL_START_CHARS)
STRIP_END_CHARS = ''.join(CL_END_CHARS)
STRIP_CHARS = ''.join(['_', ' ', '.'])

FRAGMENT_SEPARATORS = ['.', '-', '_', ' ']


CL_START = 0
CL_END = 1


class Caper(object):
    def __init__(self, debug=False):
        self.debug = debug

        self.parsers = {
            'anime': AnimeParser,
            'scene': SceneParser,
            'usenet': UsenetParser
        }

    def _closure_split(self, name):
        """
        :type name: str

        :rtype: list of CaperClosure
        """

        closures = []

        def end_closure(closures, buf):
            buf = buf.strip(STRIP_CHARS)
            if len(buf) < 2:
                return

            cur = CaperClosure(len(closures), buf)
            cur.left = closures[len(closures) - 1] if len(closures) > 0 else None

            if cur.left:
                cur.left.right = cur

            closures.append(cur)

        state = CL_START
        buf = ""
        for x, ch in enumerate(name):
            # Check for start characters
            if state == CL_START and ch in CL_START_CHARS:
                end_closure(closures, buf)

                state = CL_END
                buf = ""

            buf += ch

            if state == CL_END and ch in CL_END_CHARS:
                # End character found, create the closure
                end_closure(closures, buf)

                state = CL_START
                buf = ""
            elif state == CL_START and buf[-3:] in CL_END_STRINGS:
                # End string found, create the closure
                end_closure(closures, buf[:-3])

                state = CL_START
                buf = ""

        end_closure(closures, buf)

        return closures

    def _clean_closure(self, closure):
        """
        :type closure: str

        :rtype: str
        """

        return closure.lstrip(STRIP_START_CHARS).rstrip(STRIP_END_CHARS)

    def _fragment_split(self, closures):
        """
        :type closures: list of CaperClosure

        :rtype: list of CaperClosure
        """

        cur_position = 0
        cur = None

        def end_fragment(fragments, cur, cur_position):
            cur.position = cur_position

            cur.left = fragments[len(fragments) - 1] if len(fragments) > 0 else None
            if cur.left:
                cur.left_sep = cur.left.right_sep
                cur.left.right = cur

            cur.right_sep = ch

            fragments.append(cur)

        for closure in closures:
            closure.fragments = []

            separator_buffer = ""

            for x, ch in enumerate(self._clean_closure(closure.value)):
                if not cur:
                    cur = CaperFragment(closure)

                if ch in FRAGMENT_SEPARATORS:
                    if cur.value:
                        separator_buffer = ""

                    separator_buffer += ch

                    if cur.value or not closure.fragments:
                        end_fragment(closure.fragments, cur, cur_position)
                    elif len(separator_buffer) > 1:
                        cur.value = separator_buffer.strip()

                        if cur.value:
                            end_fragment(closure.fragments, cur, cur_position)

                        separator_buffer = ""

                    # Reset
                    cur = None
                    cur_position += 1
                else:
                    cur.value += ch

            # Finish parsing the last fragment
            if cur and cur.value:
                end_fragment(closure.fragments, cur, cur_position)

                # Reset
                cur_position = 0
                cur = None

        return closures

    def parse(self, name, parser='scene'):
        closures = self._closure_split(name)
        closures = self._fragment_split(closures)

        # Print closures
        for closure in closures:
            Logr.debug("closure [%s]", closure.value)

            for fragment in closure.fragments:
                Logr.debug("\tfragment [%s]", fragment.value)

        if parser not in self.parsers:
            raise ValueError("Unknown parser")

        # TODO autodetect the parser type
        return self.parsers[parser](self.debug).run(closures)
