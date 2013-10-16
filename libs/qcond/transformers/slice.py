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
from qcond.helpers import create_matcher
from qcond.transformers.base import Transformer


class SliceTransformer(Transformer):
    def __init__(self):
        super(SliceTransformer, self).__init__()

    def run(self, titles):
        nodes = []

        # Create a node for each title
        for title in titles:
            nodes.append(SimNode(title))

        # Calculate similarities between nodes
        for node in nodes:
            calculate_sim_links(node, [n for n in nodes if n != node])

        kill_nodes_above(nodes, 0.90)

        Logr.debug('---------------------------------------------------------------------')

        print_link_tree(nodes)
        Logr.debug('%s %s', len(nodes), [n.value for n in nodes])

        Logr.debug('---------------------------------------------------------------------')

        kill_trailing_nodes(nodes)

        Logr.debug('---------------------------------------------------------------------')

        # Sort remaining nodes by 'num_merges'
        nodes = sorted(nodes, key=lambda n: n.num_merges, reverse=True)

        print_link_tree(nodes)

        Logr.debug('---------------------------------------------------------------------')

        Logr.debug('%s %s', len(nodes), [n.value for n in nodes])

        return [n.value for n in nodes]


class SimLink(object):
    def __init__(self, similarity, opcodes, stats):
        self.similarity = similarity
        self.opcodes = opcodes
        self.stats = stats


class SimNode(object):
    def __init__(self, value):
        self.value = value

        self.dead = False
        self.num_merges = 0

        self.links = {}  # {<other SimNode>: <SimLink>}


def kill_nodes(nodes, killed_nodes):
    # Remove killed nodes from root list
    for node in killed_nodes:
        if node in nodes:
            nodes.remove(node)

    # Remove killed nodes from links
    for killed_node in killed_nodes:
        for node in nodes:
            if killed_node in node.links:
                node.links.pop(killed_node)


def kill_nodes_above(nodes, above_sim):
    killed_nodes = []

    for node in nodes:
        if node.dead:
            continue

        Logr.debug(node.value)

        for link_node, link in node.links.items():
            if link_node.dead:
                continue

            Logr.debug('\t%0.2f -- %s', link.similarity, link_node.value)

            if link.similarity >= above_sim:
                if len(link_node.value) > len(node.value):
                    Logr.debug('\t\tvery similar, killed this node')
                    link_node.dead = True
                    node.num_merges += 1
                    killed_nodes.append(link_node)
                else:
                    Logr.debug('\t\tvery similar, killed owner')
                    node.dead = True
                    link_node.num_merges += 1
                    killed_nodes.append(node)

    kill_nodes(nodes, killed_nodes)


def print_link_tree(nodes):
    for node in nodes:
        Logr.debug(node.value)
        Logr.debug('\tnum_merges: %s', node.num_merges)

        if len(node.links):
            Logr.debug('\t========== LINKS ==========')
            for link_node, link in node.links.items():
                Logr.debug('\t%0.2f -- %s', link.similarity, link_node.value)

            Logr.debug('\t---------------------------')


def kill_trailing_nodes(nodes):
    killed_nodes = []

    for node in nodes:
        if node.dead:
            continue

        Logr.debug(node.value)

        for link_node, link in node.links.items():
            if link_node.dead:
                continue

            is_valid = link.stats.get('valid', False)

            has_deletions = False
            has_insertions = False
            has_replacements = False

            for opcode in link.opcodes:
                if opcode[0] == 'delete':
                    has_deletions = True
                if opcode[0] == 'insert':
                    has_insertions = True
                if opcode[0] == 'replace':
                    has_replacements = True

            equal_perc = link.stats.get('equal', 0) / float(len(node.value))
            insert_perc = link.stats.get('insert', 0) / float(len(node.value))

            Logr.debug('\t({0:<24}) [{1:02d}:{2:02d} = {3:02d} {4:3.0f}% {5:3.0f}%] -- {6:<45}'.format(
                'd:%s, i:%s, r:%s' % (has_deletions, has_insertions, has_replacements),
                len(node.value), len(link_node.value), link.stats.get('equal', 0),
                equal_perc * 100, insert_perc * 100,
                '"{0}"'.format(link_node.value)
            ))

            Logr.debug('\t\t%s', link.stats)

            kill = all([
                is_valid,
                equal_perc >= 0.5,
                insert_perc < 2,
                has_insertions,
                not has_deletions,
                not has_replacements
            ])

            if kill:
                Logr.debug('\t\tkilled this node')

                link_node.dead = True
                node.num_merges += 1
                killed_nodes.append(link_node)

    kill_nodes(nodes, killed_nodes)

stats_print_format = "\t{0:<8} ({1:2d}:{2:2d}) ({3:2d}:{4:2d})"


def get_index_values(iterable, a, b):
    return (
        iterable[a] if a else None,
        iterable[b] if b else None
    )


def get_indices(iterable, a, b):
    return (
        a if 0 < a < len(iterable) else None,
        b if 0 < b < len(iterable) else None
    )


def get_opcode_stats(for_node, node, opcodes):
    stats = {}

    for tag, i1, i2, j1, j2 in opcodes:
        Logr.debug(stats_print_format.format(
            tag, i1, i2, j1, j2
        ))

        if tag in ['insert', 'delete']:
            ax = None, None
            bx = None, None

            if tag == 'insert':
                ax = get_indices(for_node.value, i1 - 1, i1)
                bx = get_indices(node.value, j1, j2 - 1)

            if tag == 'delete':
                ax = get_indices(for_node.value, j1 - 1, j1)
                bx = get_indices(node.value, i1, i2 - 1)

            av = get_index_values(for_node.value, *ax)
            bv = get_index_values(node.value, *bx)

            Logr.debug(
                '\t\t%s %s [%s><%s] <---> %s %s [%s><%s]',
                ax, av, av[0], av[1],
                bx, bv, bv[0], bv[1]
            )

            head_valid = av[0] in [None, ' '] or bv[0] in [None, ' ']
            tail_valid = av[1] in [None, ' '] or bv[1] in [None, ' ']
            valid = head_valid and tail_valid

            if 'valid' not in stats or (stats['valid'] and not valid):
                stats['valid'] = valid

            Logr.debug('\t\t' + ('VALID' if valid else 'INVALID'))

        if tag not in stats:
            stats[tag] = 0

        stats[tag] += (i2 - i1) or (j2 - j1)

    return stats


def calculate_sim_links(for_node, other_nodes):
    for node in other_nodes:
        if node in for_node.links:
            continue

        Logr.debug('calculating similarity between "%s" and "%s"', for_node.value, node.value)

        # Get similarity
        similarity_matcher = create_matcher(for_node.value, node.value)
        similarity = similarity_matcher.quick_ratio()

        # Get for_node -> node opcodes
        a_opcodes_matcher = create_matcher(for_node.value, node.value, swap_longest = False)
        a_opcodes = a_opcodes_matcher.get_opcodes()
        a_stats = get_opcode_stats(for_node, node, a_opcodes)

        Logr.debug('-' * 100)

        # Get node -> for_node opcodes
        b_opcodes_matcher = create_matcher(node.value, for_node.value, swap_longest = False)
        b_opcodes = b_opcodes_matcher.get_opcodes()
        b_stats = get_opcode_stats(for_node, node, b_opcodes)

        for_node.links[node] = SimLink(similarity, a_opcodes, a_stats)
        node.links[for_node] = SimLink(similarity, b_opcodes, b_stats)

        #raw_input('Press ENTER to continue')
