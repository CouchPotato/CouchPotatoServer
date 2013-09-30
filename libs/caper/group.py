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
from caper.helpers import clean_dict
from caper.result import CaperFragmentNode
from caper.step import CaptureStep
from caper.constraint import CaptureConstraint


class CaptureGroup(object):
    def __init__(self, parser, result):
        """Capture group object

        :type parser: caper.parsers.base.Parser
        :type result: caper.result.CaperResult
        """

        self.parser = parser
        self.result = result

        #: @type: list of CaptureStep
        self.steps = []
        #: @type: list of CaptureConstraint
        self.constraints = []

    def capture_fragment(self, tag, regex=None, func=None, single=True):
        Logr.debug('capture_fragment("%s", "%s", %s, %s)', tag, regex, func, single)

        self.steps.append(CaptureStep(
            self, tag,
            'fragment',
            regex=regex,
            func=func,
            single=single
        ))

        return self

    def capture_closure(self, tag, regex=None, func=None, single=True):
        Logr.debug('capture_closure("%s", "%s", %s, %s)', tag, regex, func, single)

        self.steps.append(CaptureStep(
            self, tag,
            'closure',
            regex=regex,
            func=func,
            single=single
        ))

        return self

    def until(self, **kwargs):
        self.constraints.append(CaptureConstraint(self, **kwargs))

        return self

    def parse_subject(self, parent_head, subject):
        parent_node = parent_head[0] if type(parent_head) is list else parent_head

        # TODO - if subject is a closure?

        nodes = []

        # Check constraints
        for constraint in self.constraints:
            weight, success = constraint.execute(subject)
            if success:
                Logr.debug('capturing broke on "%s" at %s', subject.value, constraint)
                parent_node.finished_groups.append(self)
                nodes.append(parent_head)

                if weight == 1.0:
                    return nodes
                else:
                    Logr.debug('Branching result')

        # Try match subject against the steps available
        tag, success, weight, match, num_fragments = (None, None, None, None, None)
        for step in self.steps:
            tag = step.tag
            success, weight, match, num_fragments = step.execute(subject)
            if success:
                match = clean_dict(match) if type(match) is dict else match
                Logr.debug('Found match with weight %s, match: %s, num_fragments: %s' % (weight, match, num_fragments))
                break

        Logr.debug('created fragment node with subject.value: "%s"' % subject.value)

        result = [CaperFragmentNode(parent_node.closure, subject.take_right(num_fragments), parent_head, tag, weight, match)]

        if match and weight < 1.0:
            if num_fragments == 1:
                result.append(CaperFragmentNode(parent_node.closure, [subject], parent_head, None, None, None))
            else:
                nodes.append(CaperFragmentNode(parent_node.closure, [subject], parent_head, None, None, None))

        nodes.append(result[0] if len(result) == 1 else result)

        return nodes

    def execute(self):
        heads_finished = None

        while heads_finished is None or not (len(heads_finished) == len(self.result.heads) and all(heads_finished)):
            heads_finished = []

            heads = self.result.heads
            self.result.heads = []

            for head in heads:
                node = head[0] if type(head) is list else head

                Logr.debug("head node: %s" % node)

                if self in node.finished_groups:
                    Logr.debug("head finished for group")
                    self.result.heads.append(head)
                    heads_finished.append(True)
                    continue

                next_subject = node.next()

                if next_subject:
                    for node_result in self.parse_subject(head, next_subject):
                        self.result.heads.append(node_result)

                heads_finished.append(self in node.finished_groups or next_subject is None)

            if len(self.result.heads) == 0:
                self.result.heads = heads

            Logr.debug("heads_finished: %s, self.result.heads: %s", heads_finished, self.result.heads)

        Logr.debug("group finished")
