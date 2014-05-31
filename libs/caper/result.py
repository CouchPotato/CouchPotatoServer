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

import copy
from logr import Logr


GROUP_MATCHES = ['identifier']


class CaperNode(object):
    def __init__(self, closure, parent=None, match=None):
        """
        :type parent: CaperNode
        :type weight: float
        """

        #: :type: caper.objects.CaperClosure
        self.closure = closure

        #: :type: CaperNode
        self.parent = parent

        #: :type: CaptureMatch
        self.match = match

        #: :type: list of CaptureGroup
        self.finished_groups = []

    def next(self):
        raise NotImplementedError()

    def captured(self):
        cur = self

        if cur.match:
            yield cur.match.tag, cur.match.result

        while cur.parent:
            cur = cur.parent

            if cur.match:
                yield cur.match.tag, cur.match.result


class CaperRootNode(CaperNode):
    def __init__(self, closure):
        """
        :type closure: caper.objects.CaperClosure or list of caper.objects.CaperClosure
        """
        super(CaperRootNode, self).__init__(closure)

    def next(self):
        return self.closure


class CaperClosureNode(CaperNode):
    def __init__(self, closure, parent=None, match=None):
        """
        :type closure: caper.objects.CaperClosure or list of caper.objects.CaperClosure
        """
        super(CaperClosureNode, self).__init__(closure, parent, match)

    def next(self):
        if not self.closure:
            return None

        if self.match:
            # Jump to next closure if we have a match
            return self.closure.right
        elif len(self.closure.fragments) > 0:
            # Otherwise parse the fragments
            return self.closure.fragments[0]

        return None

    def __str__(self):
        return "<CaperClosureNode match: %s>" % repr(self.match)

    def __repr__(self):
        return self.__str__()


class CaperFragmentNode(CaperNode):
    def __init__(self, closure, fragments, parent=None, match=None):
        """
        :type closure: caper.objects.CaperClosure
        :type fragments: list of caper.objects.CaperFragment
        """
        super(CaperFragmentNode, self).__init__(closure, parent, match)

        #: :type: caper.objects.CaperFragment or list of caper.objects.CaperFragment
        self.fragments = fragments

    def next(self):
        if len(self.fragments) > 0 and self.fragments[-1] and self.fragments[-1].right:
            return self.fragments[-1].right

        if self.closure.right:
            return self.closure.right

        return None

    def __str__(self):
        return "<CaperFragmentNode match: %s>" % repr(self.match)

    def __repr__(self):
        return self.__str__()


class CaperResult(object):
    def __init__(self):
        #: :type: list of CaperNode
        self.heads = []

        self.chains = []

    def build(self):
        max_matched = 0

        for head in self.heads:
            for chain in self.combine_chain(head):
                if chain.num_matched > max_matched:
                    max_matched = chain.num_matched

                self.chains.append(chain)

        for chain in self.chains:
            chain.weights.append(chain.num_matched / float(max_matched or chain.num_matched or 1))
            chain.finish()

        self.chains.sort(key=lambda chain: chain.weight, reverse=True)

        for chain in self.chains:
            Logr.debug("chain weight: %.02f", chain.weight)
            Logr.debug("\tInfo: %s", chain.info)

            Logr.debug("\tWeights: %s", chain.weights)
            Logr.debug("\tNumber of Fragments Matched: %s", chain.num_matched)

    def combine_chain(self, subject, chain=None):
        nodes = subject if type(subject) is list else [subject]

        if chain is None:
            chain = CaperResultChain()

        result = []

        for x, node in enumerate(nodes):
            node_chain = chain if x == len(nodes) - 1 else chain.copy()

            if not node.parent:
                result.append(node_chain)
                continue

            node_chain.update(node)
            result.extend(self.combine_chain(node.parent, node_chain))

        return result


class CaperResultChain(object):
    def __init__(self):
        #: :type: float
        self.weight = None
        self.info = {}
        self.num_matched = 0

        self.weights = []

    def update(self, subject):
        """
        :type subject: CaperFragmentNode
        """
        if not subject.match or not subject.match.success:
            return

        # TODO this should support closure nodes
        if type(subject) is CaperFragmentNode:
            self.num_matched += len(subject.fragments) if subject.fragments is not None else 0

        self.weights.append(subject.match.weight)

        if subject.match:
            if subject.match.tag not in self.info:
                self.info[subject.match.tag] = []

            self.info[subject.match.tag].insert(0, subject.match.result)

    def finish(self):
        self.weight = sum(self.weights) / len(self.weights)

    def copy(self):
        chain = CaperResultChain()

        chain.weight = self.weight
        chain.info = copy.deepcopy(self.info)

        chain.num_matched = self.num_matched
        chain.weights = copy.copy(self.weights)

        return chain