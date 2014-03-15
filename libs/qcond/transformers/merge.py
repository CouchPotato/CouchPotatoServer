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


from operator import itemgetter
from logr import Logr
from qcond.helpers import simplify, strip, first, sorted_append, distinct
from qcond.transformers.base import Transformer
from qcond.compat import xrange


class MergeTransformer(Transformer):
    def __init__(self):
        super(MergeTransformer, self).__init__()

    def run(self, titles):
        titles = distinct([simplify(title) for title in titles])

        Logr.info(str(titles))

        Logr.debug("------------------------------------------------------------")

        root, tails = self.parse(titles)

        Logr.debug("--------------------------PARSE-----------------------------")

        for node in root:
            print_tree(node)

        Logr.debug("--------------------------MERGE-----------------------------")

        self.merge(root)

        Logr.debug("--------------------------FINAL-----------------------------")

        for node in root:
            print_tree(node)

        Logr.debug("--------------------------RESULT-----------------------------")

        scores = {}
        results = []

        for tail in tails:
            score, value, original_value = tail.full_value()

            if value in scores:
                scores[value] += score
            else:
                results.append((value, original_value))
                scores[value] = score

                Logr.debug("%s %s %s", score, value, original_value)

        sorted_results = sorted(results, key=lambda item: (scores[item[0]], item[1]), reverse = True)

        return [result[0] for result in sorted_results]

    def parse(self, titles):
        root = []
        tails = []

        for title in titles:
            Logr.debug(title)

            cur = None
            words = title.split(' ')

            for wx in xrange(len(words)):
                word = strip(words[wx])

                if cur is None:
                    cur = find_node(root, word)

                    if cur is None:
                        cur = DNode(word, None, num_children=len(words) - wx, original_value=title)
                        root.append(cur)
                else:
                    parent = cur
                    parent.weight += 1

                    cur = find_node(parent.right, word)

                    if cur is None:
                        Logr.debug("%s %d", word, len(words) - wx)
                        cur = DNode(word, parent, num_children=len(words) - wx)
                        sorted_append(parent.right, cur, lambda a: a.num_children < cur.num_children)
                    else:
                        cur.weight += 1

            tails.append(cur)

        return root, tails

    def merge(self, root):
        for x in range(len(root)):
            Logr.debug(root[x])
            root[x].right = self._merge(root[x].right)
            Logr.debug('=================================================================')

        return root

    def get_nodes_right(self, value):
        if type(value) is not list:
            value = [value]

        nodes = []

        for node in value:
            nodes.append(node)

            for child in self.get_nodes_right(node.right):
                nodes.append(child)

        return nodes

    def destroy_nodes_right(self, value):
        nodes = self.get_nodes_right(value)

        for node in nodes:
            node.value = None
            node.dead = True

    def _merge(self, nodes, depth = 0):
        Logr.debug(str('\t' * depth) + str(nodes))

        if not len(nodes):
            return []

        top = nodes[0]

        # Merge into top
        for x in range(len(nodes)):
            # Merge extra results into top
            if x > 0:
                top.value = None
                top.weight += nodes[x].weight
                self.destroy_nodes_right(top.right)

                if len(nodes[x].right):
                    top.join_right(nodes[x].right)

                    Logr.debug("= %s joined %s", nodes[x], top)

                nodes[x].dead = True

        nodes = [n for n in nodes if not n.dead]

        # Traverse further
        for node in nodes:
            if len(node.right):
                node.right = self._merge(node.right, depth + 1)

        return nodes


def print_tree(node, depth = 0):
    Logr.debug(str('\t' * depth) + str(node))

    if len(node.right):
        for child in node.right:
            print_tree(child, depth + 1)
    else:
        Logr.debug(node.full_value()[1])


def find_node(node_list, value):
    # Try find adjacent node match
    for node in node_list:
        if node.value == value:
            return node

    return None


class DNode(object):
    def __init__(self, value, parent, right=None, weight=1, num_children=None, original_value=None):
        self.value = value

        self.parent = parent

        if right is None:
            right = []
        self.right = right

        self.weight = weight

        self.original_value = original_value
        self.num_children = num_children

        self.dead = False

    def join_right(self, nodes):
        for node in nodes:
            duplicate = first(lambda x: x.value == node.value, self.right)

            if duplicate:
                duplicate.weight += node.weight
                duplicate.join_right(node.right)
            else:
                node.parent = self
                self.right.append(node)

    def full_value(self):
        words = []
        total_score = 0

        cur = self
        root = None

        while cur is not None:
            if cur.value and not cur.dead:
                words.insert(0, cur.value)
                total_score += cur.weight

            if cur.parent is None:
                root = cur
            cur = cur.parent

        return float(total_score) / len(words), ' '.join(words), root.original_value if root else None

    def __repr__(self):
        return '<%s value:"%s", weight: %s, num_children: %s%s%s>' % (
            'DNode',
            self.value,
            self.weight,
            self.num_children,
            (', original_value: %s' % self.original_value) if self.original_value else '',
            ' REMOVING' if self.dead else ''
        )
