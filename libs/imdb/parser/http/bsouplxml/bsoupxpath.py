"""
parser.http.bsoupxpath module (imdb.parser.http package).

This module provides XPath support for BeautifulSoup.

Copyright 2008 H. Turgut Uyar <uyar@tekir.org>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

__author__ = 'H. Turgut Uyar <uyar@tekir.org>'
__docformat__ = 'restructuredtext'


import re
import string
import _bsoup as BeautifulSoup


# XPath related enumerations and constants

AXIS_ANCESTOR          = 'ancestor'
AXIS_ATTRIBUTE         = 'attribute'
AXIS_CHILD             = 'child'
AXIS_DESCENDANT        = 'descendant'
AXIS_FOLLOWING         = 'following'
AXIS_FOLLOWING_SIBLING = 'following-sibling'
AXIS_PRECEDING_SIBLING = 'preceding-sibling'

AXES = (AXIS_ANCESTOR, AXIS_ATTRIBUTE, AXIS_CHILD, AXIS_DESCENDANT,
        AXIS_FOLLOWING, AXIS_FOLLOWING_SIBLING, AXIS_PRECEDING_SIBLING)

XPATH_FUNCTIONS = ('starts-with', 'string-length')


def tokenize_path(path):
    """Tokenize a location path into location steps. Return the list of steps.

    If two steps are separated by a double slash, the double slashes are part of
    the second step. If they are separated by only one slash, the slash is not
    included in any of the steps.
    """
    # form a list of tuples that mark the start and end positions of steps
    separators = []
    last_position = 0
    i = -1
    in_string = False
    while i < len(path) - 1:
        i = i + 1
        if path[i] == "'":
            in_string = not in_string
        if in_string:
            # slashes within strings are not step separators
            continue
        if path[i] == '/':
            if i > 0:
                separators.append((last_position, i))
            if (path[i+1] == '/'):
                last_position = i
                i = i + 1
            else:
                last_position = i + 1
    separators.append((last_position, len(path)))

    steps = []
    for start, end in separators:
        steps.append(path[start:end])
    return steps


class Path:
    """A location path.
    """

    def __init__(self, path, parse=True):
        self.path = path
        self.steps = []
        if parse:
            if (path[0] == '/') and (path[1] != '/'):
                # if not on the descendant axis, remove the leading slash
                path = path[1:]
            steps = tokenize_path(path)
            for step in steps:
                self.steps.append(PathStep(step))

    def apply(self, node):
        """Apply the path to a node. Return the resulting list of nodes.

        Apply the steps in the path sequentially by sending the output of each
        step as input to the next step.
        """
        # FIXME: this should return a node SET, not a node LIST
        # or at least a list with no duplicates
        if self.path[0] == '/':
            # for an absolute path, start from the root
            if not isinstance(node, BeautifulSoup.Tag) \
               or (node.name != '[document]'):
                node = node.findParent('[document]')
        nodes = [node]
        for step in self.steps:
            nodes = step.apply(nodes)
        return nodes


class PathStep:
    """A location step in a location path.
    """

    AXIS_PATTERN          = r"""(%s)::|@""" % '|'.join(AXES)
    NODE_TEST_PATTERN     = r"""\w+(\(\))?"""
    PREDICATE_PATTERN     = r"""\[(.*?)\]"""
    LOCATION_STEP_PATTERN = r"""(%s)?(%s)((%s)*)""" \
                          % (AXIS_PATTERN, NODE_TEST_PATTERN, PREDICATE_PATTERN)

    _re_location_step = re.compile(LOCATION_STEP_PATTERN)

    PREDICATE_NOT_PATTERN = r"""not\((.*?)\)"""
    PREDICATE_AXIS_PATTERN = r"""(%s)?(%s)(='(.*?)')?""" \
                           % (AXIS_PATTERN, NODE_TEST_PATTERN)
    PREDICATE_FUNCTION_PATTERN = r"""(%s)\(([^,]+(,\s*[^,]+)*)?\)(=(.*))?""" \
                               % '|'.join(XPATH_FUNCTIONS)

    _re_predicate_not = re.compile(PREDICATE_NOT_PATTERN)
    _re_predicate_axis = re.compile(PREDICATE_AXIS_PATTERN)
    _re_predicate_function = re.compile(PREDICATE_FUNCTION_PATTERN)

    def __init__(self, step):
        self.step = step
        if (step == '.') or (step == '..'):
            return

        if step[:2] == '//':
            default_axis = AXIS_DESCENDANT
            step = step[2:]
        else:
            default_axis = AXIS_CHILD

        step_match = self._re_location_step.match(step)

        # determine the axis
        axis = step_match.group(1)
        if axis is None:
            self.axis = default_axis
        elif axis == '@':
            self.axis = AXIS_ATTRIBUTE
        else:
            self.axis = step_match.group(2)

        self.soup_args = {}
        self.index = None

        self.node_test = step_match.group(3)
        if self.node_test == 'text()':
            self.soup_args['text'] = True
        else:
            self.soup_args['name'] = self.node_test

        self.checkers = []
        predicates = step_match.group(5)
        if predicates is not None:
            predicates = [p for p in predicates[1:-1].split('][') if p]
            for predicate in predicates:
                checker = self.__parse_predicate(predicate)
                if checker is not None:
                    self.checkers.append(checker)

    def __parse_predicate(self, predicate):
        """Parse the predicate. Return a callable that can be used to filter
        nodes. Update `self.soup_args` to take advantage of BeautifulSoup search
        features.
        """
        try:
            position = int(predicate)
            if self.axis == AXIS_DESCENDANT:
                return PredicateFilter('position', value=position)
            else:
                # use the search limit feature instead of a checker
                self.soup_args['limit'] = position
                self.index = position - 1
                return None
        except ValueError:
            pass

        if predicate == "last()":
            self.index = -1
            return None

        negate = self._re_predicate_not.match(predicate)
        if negate:
            predicate = negate.group(1)

        function_match = self._re_predicate_function.match(predicate)
        if function_match:
            name = function_match.group(1)
            arguments = function_match.group(2)
            value = function_match.group(4)
            if value is not None:
                value = function_match.group(5)
            return PredicateFilter(name, arguments, value)

        axis_match = self._re_predicate_axis.match(predicate)
        if axis_match:
            axis = axis_match.group(1)
            if axis is None:
                axis = AXIS_CHILD
            elif axis == '@':
                axis = AXIS_ATTRIBUTE
            if axis == AXIS_ATTRIBUTE:
                # use the attribute search feature instead of a checker
                attribute_name = axis_match.group(3)
                if axis_match.group(5) is not None:
                    attribute_value = axis_match.group(6)
                elif not negate:
                    attribute_value = True
                else:
                    attribute_value = None
                if not self.soup_args.has_key('attrs'):
                    self.soup_args['attrs'] = {}
                self.soup_args['attrs'][attribute_name] = attribute_value
                return None
            elif axis == AXIS_CHILD:
                node_test = axis_match.group(3)
                node_value = axis_match.group(6)
                return PredicateFilter('axis', node_test, value=node_value,
                                       negate=negate)

        raise NotImplementedError("This predicate is not implemented")

    def apply(self, nodes):
        """Apply the step to a list of nodes. Return the list of nodes for the
        next step.
        """
        if self.step == '.':
            return nodes
        elif self.step == '..':
            return [node.parent for node in nodes]

        result = []
        for node in nodes:
            if self.axis == AXIS_CHILD:
                found = node.findAll(recursive=False, **self.soup_args)
            elif self.axis == AXIS_DESCENDANT:
                found = node.findAll(recursive=True, **self.soup_args)
            elif self.axis == AXIS_ATTRIBUTE:
                try:
                    found = [node[self.node_test]]
                except KeyError:
                    found = []
            elif self.axis == AXIS_FOLLOWING_SIBLING:
                found = node.findNextSiblings(**self.soup_args)
            elif self.axis == AXIS_PRECEDING_SIBLING:
                # TODO: make sure that the result is reverse ordered
                found = node.findPreviousSiblings(**self.soup_args)
            elif self.axis == AXIS_FOLLOWING:
                # find the last descendant of this node
                last = node
                while (not isinstance(last, BeautifulSoup.NavigableString)) \
                      and (len(last.contents) > 0):
                    last = last.contents[-1]
                found = last.findAllNext(**self.soup_args)
            elif self.axis == AXIS_ANCESTOR:
                found = node.findParents(**self.soup_args)

            # this should only be active if there is a position predicate
            # and the axis is not 'descendant'
            if self.index is not None:
                if found:
                    if len(found) > self.index:
                        found = [found[self.index]]
                    else:
                        found = []

            if found:
                for checker in self.checkers:
                    found = filter(checker, found)
                result.extend(found)

        return result


class PredicateFilter:
    """A callable class for filtering nodes.
    """

    def __init__(self, name, arguments=None, value=None, negate=False):
        self.name = name
        self.arguments = arguments
        self.negate = negate

        if name == 'position':
            self.__filter = self.__position
            self.value = value
        elif name == 'axis':
            self.__filter = self.__axis
            self.node_test = arguments
            self.value = value
        elif name == 'starts-with':
            self.__filter = self.__starts_with
            args = map(string.strip, arguments.split(','))
            if args[0][0] == '@':
                self.arguments = (True, args[0][1:], args[1][1:-1])
            else:
                self.arguments = (False, args[0], args[1][1:-1])
        elif name == 'string-length':
            self.__filter = self.__string_length
            args = map(string.strip, arguments.split(','))
            if args[0][0] == '@':
                self.arguments = (True, args[0][1:])
            else:
                self.arguments = (False, args[0])
            self.value = int(value)
        else:
            raise NotImplementedError("This XPath function is not implemented")

    def __call__(self, node):
        if self.negate:
            return not self.__filter(node)
        else:
            return self.__filter(node)

    def __position(self, node):
        if isinstance(node, BeautifulSoup.NavigableString):
            actual_position = len(node.findPreviousSiblings(text=True)) + 1
        else:
            actual_position = len(node.findPreviousSiblings(node.name)) + 1
        return actual_position == self.value

    def __axis(self, node):
        if self.node_test == 'text()':
            return node.string == self.value
        else:
            children = node.findAll(self.node_test, recursive=False)
            if len(children) > 0 and self.value is None:
                return True
            for child in children:
                if child.string == self.value:
                    return True
            return False

    def __starts_with(self, node):
        if self.arguments[0]:
            # this is an attribute
            attribute_name = self.arguments[1]
            if node.has_key(attribute_name):
                first = node[attribute_name]
                return first.startswith(self.arguments[2])
        elif self.arguments[1] == 'text()':
            first = node.contents[0]
            if isinstance(first, BeautifulSoup.NavigableString):
                return first.startswith(self.arguments[2])
        return False

    def __string_length(self, node):
        if self.arguments[0]:
            # this is an attribute
            attribute_name = self.arguments[1]
            if node.has_key(attribute_name):
                value = node[attribute_name]
            else:
                value = None
        elif self.arguments[1] == 'text()':
            value = node.string
        if value is not None:
            return len(value) == self.value
        return False


_paths = {}
_steps = {}

def get_path(path):
    """Utility for eliminating repeated parsings of the same paths and steps.
    """
    if not _paths.has_key(path):
        p = Path(path, parse=False)
        steps = tokenize_path(path)
        for step in steps:
            if not _steps.has_key(step):
                _steps[step] = PathStep(step)
            p.steps.append(_steps[step])
        _paths[path] = p
    return _paths[path]
