from __future__ import print_function

import re

# Super dumb little selector parser.

# Yes, yes, this is a regex tokenizer.  The actual meaning of the
# selector doesn't matter; the parts are just important for matching up
# during @extend.

# Selectors have three levels: simple, combinator, comma-delimited.
# Each combinator can only appear once as a delimiter between simple
# selectors, so it can be thought of as a prefix.
# So this:
#     a.b + c, d#e
# parses into two Selectors with these structures:
#     [[' ', 'a', '.b'], ['+', 'c']]
#     [[' ', 'd', '#e']]
# Note that the first simple selector has an implied descendant
# combinator -- i.e., it is a descendant of the root element.
# TODO `*html` is incorrectly parsed as a single selector
# TODO this oughta be touched up for css4 selectors
SELECTOR_TOKENIZER = re.compile(r'''
    # Colons introduce pseudo-selectors, sometimes with parens
    # TODO doesn't handle quoted )
    [:]+ [-\w]+ (?: [(] .+? [)] )?

    # These guys are combinators -- note that a single space counts too
    | \s* [ +>~,] \s*

    # Square brackets are attribute tests
    # TODO: this doesn't handle ] within a string
    | [[] .+? []]

    # Dot and pound start class/id selectors.  Percent starts a Sass
    # extend-target faux selector.
    | [.#%] [-\w]+

    # Percentages are used for @keyframes
    | [-.\d]+ [%]

    # Plain identifiers, or single asterisks, are element names
    | [-\w]+
    | [*]

    # & is the sass replacement token
    | [&]

    # And as a last-ditch effort, just eat up to whitespace
    | (\S+)
''', re.VERBOSE | re.MULTILINE)


# Maps the first character of a token to a rough ordering.  The default
# (element names) is zero.
TOKEN_TYPE_ORDER = {
    '#': 2,
    '.': 3,
    '[': 3,
    ':': 3,
    '%': 4,
}
TOKEN_SORT_KEY = lambda token: TOKEN_TYPE_ORDER.get(token[0], 0)


def _is_combinator_subset_of(specific, general, is_first=True):
    """Return whether `specific` matches a non-strict subset of what `general`
    matches.
    """
    if is_first and general == ' ':
        # First selector always has a space to mean "descendent of root", which
        # still holds if any other selector appears above it
        return True

    if specific == general:
        return True

    if specific == '>' and general == ' ':
        return True

    if specific == '+' and general == '~':
        return True

    return False


class SimpleSelector(object):
    """A simple selector, by CSS 2.1 terminology: a combination of element
    name, class selectors, id selectors, and other criteria that all apply to a
    single element.

    Note that CSS 3 considers EACH of those parts to be a "simple selector",
    and calls a group of them a "sequence of simple selectors".  That's a
    terrible class name, so we're going with 2.1 here.

    For lack of a better name, each of the individual parts is merely called a
    "token".
    """
    def __init__(self, combinator, tokens):
        self.combinator = combinator
        # TODO enforce that only one element name (including *) appears in a
        # selector
        # TODO remove duplicates
        self.tokens = tuple(sorted(tokens, key=TOKEN_SORT_KEY))

    def __repr__(self):
        return "<%s: %r>" % (type(self).__name__, self.render())

    def __hash__(self):
        return hash((self.combinator, self.tokens))

    def __eq__(self, other):
        if not isinstance(other, SimpleSelector):
            return NotImplemented

        return (
            self.combinator == other.combinator and
            self.tokens == other.tokens)

    @property
    def has_parent_reference(self):
        return '&' in self.tokens or 'self' in self.tokens

    @property
    def has_placeholder(self):
        return any(
            token[0] == '%'
            for token in self.tokens)

    def is_superset_of(self, other, soft_combinator=False):
        """Return True iff this selector matches the same elements as `other`,
        and perhaps others.

        That is, ``.foo`` is a superset of ``.foo.bar``, because the latter is
        more specific.

        Set `soft_combinator` true to ignore the specific case of this selector
        having a descendent combinator and `other` having anything else.  This
        is for superset checking for ``@extend``, where a space combinator
        really means "none".
        """
        # Combinators must match, OR be compatible -- space is a superset of >,
        # ~ is a superset of +
        if soft_combinator and self.combinator == ' ':
            combinator_superset = True
        else:
            combinator_superset = (
                self.combinator == other.combinator or
                (self.combinator == ' ' and other.combinator == '>') or
                (self.combinator == '~' and other.combinator == '+'))

        return (
            combinator_superset and
            set(self.tokens) <= set(other.tokens))

    def replace_parent(self, parent_simples):
        """If ``&`` (or the legacy xCSS equivalent ``self``) appears in this
        selector, replace it with the given iterable of parent selectors.

        Returns a tuple of simple selectors.
        """
        assert parent_simples

        ancestors = parent_simples[:-1]
        parent = parent_simples[-1]

        did_replace = False
        new_tokens = []
        for token in self.tokens:
            if not did_replace and token in ('&', 'self'):
                did_replace = True
                new_tokens.extend(parent.tokens)
            else:
                new_tokens.append(token)

        if not did_replace:
            # This simple selector doesn't contain a parent reference so just
            # stick it on the end
            return parent_simples + (self,)

        # This simple selector was merged into the direct parent.
        merged_self = type(self)(parent.combinator, new_tokens)
        selector = ancestors + (merged_self,)
        # Our combinator goes on the first ancestor, i.e., substituting "foo
        # bar baz" into "+ &.quux" produces "+ foo bar baz.quux".  This means a
        # potential conflict with the first ancestor's combinator!
        root = selector[0]
        if not _is_combinator_subset_of(self.combinator, root.combinator):
            raise ValueError(
                "Can't sub parent {0!r} into {1!r}: "
                "combinators {2!r} and {3!r} conflict!"
                .format(
                    parent_simples, self, self.combinator, root.combinator))

        root = type(self)(self.combinator, root.tokens)
        selector = (root,) + selector[1:]
        return tuple(selector)

    # TODO just use set ops for these, once the constructor removes dupes
    def merge_with(self, other):
        new_tokens = self.tokens + tuple(token for token in other.tokens if token not in set(self.tokens))
        return type(self)(self.combinator, new_tokens)

    def difference(self, other):
        new_tokens = tuple(token for token in self.tokens if token not in set(other.tokens))
        return type(self)(self.combinator, new_tokens)

    def render(self):
        # TODO fail if there are no tokens, or if one is a placeholder?
        rendered = ''.join(self.tokens)
        if self.combinator != ' ':
            rendered = ' '.join((self.combinator, rendered))

        return rendered


class Selector(object):
    """A single CSS selector."""

    def __init__(self, simples):
        """Return a selector containing a sequence of `SimpleSelector`s.

        You probably want to use `parse_many` or `parse_one` instead.
        """
        # TODO enforce uniqueness
        self.simple_selectors = tuple(simples)

    @classmethod
    def parse_many(cls, selector):
        selector = selector.strip()
        ret = []

        pending = dict(
            simples=[],
            combinator=' ',
            tokens=[],
        )

        def promote_simple():
            if pending['tokens']:
                pending['simples'].append(
                    SimpleSelector(pending['combinator'], pending['tokens']))
                pending['combinator'] = ' '
                pending['tokens'] = []

        def promote_selector():
            promote_simple()
            if pending['simples']:
                ret.append(cls(pending['simples']))
            pending['simples'] = []

        pos = 0
        while pos < len(selector):
            # TODO i don't think this deals with " + " correctly.  anywhere.
            # TODO this used to turn "1.5%" into empty string; why does error
            # not work?
            m = SELECTOR_TOKENIZER.match(selector, pos)
            if not m:
                # TODO prettify me
                raise SyntaxError("Couldn't parse selector: %r" % (selector,))

            token = m.group(0)
            pos += len(token)

            # Kill any extraneous space, BUT make sure not to turn a lone space
            # into an empty string
            token = token.strip() or ' '

            if token == ',':
                # End current selector
                # TODO what about "+ ,"?  what do i even do with that
                promote_selector()
            elif token in ' +>~':
                # End current simple selector
                promote_simple()
                pending['combinator'] = token
            else:
                # Add to pending simple selector
                pending['tokens'].append(token)

        # Deal with any remaining pending bits
        promote_selector()

        return ret

    @classmethod
    def parse_one(cls, selector_string):
        selectors = cls.parse_many(selector_string)
        if len(selectors) != 1:
            # TODO better error
            raise ValueError

        return selectors[0]

    def __repr__(self):
        return "<%s: %r>" % (type(self).__name__, self.render())

    def __hash__(self):
        return hash(self.simple_selectors)

    def __eq__(self, other):
        if not isinstance(other, Selector):
            return NotImplemented

        return self.simple_selectors == other.simple_selectors

    @property
    def has_parent_reference(self):
        return any(
            simple.has_parent_reference
            for simple in self.simple_selectors)

    @property
    def has_placeholder(self):
        return any(
            simple.has_placeholder
            for simple in self.simple_selectors)

    def with_parent(self, parent):
        saw_parent_ref = False

        new_simples = []
        for simple in self.simple_selectors:
            if simple.has_parent_reference:
                new_simples.extend(simple.replace_parent(parent.simple_selectors))
                saw_parent_ref = True
            else:
                new_simples.append(simple)

        if not saw_parent_ref:
            new_simples = parent.simple_selectors + tuple(new_simples)

        return type(self)(new_simples)

    def lookup_key(self):
        """Build a key from the "important" parts of a selector: elements,
        classes, ids.
        """
        parts = set()
        for node in self.simple_selectors:
            for token in node.tokens:
                if token[0] not in ':[':
                    parts.add(token)

        if not parts:
            # Should always have at least ONE key; selectors with no elements,
            # no classes, and no ids can be indexed as None to avoid a scan of
            # every selector in the entire document
            parts.add(None)

        return frozenset(parts)

    def is_superset_of(self, other):
        assert isinstance(other, Selector)

        idx = 0
        for other_node in other.simple_selectors:
            if idx >= len(self.simple_selectors):
                return False

            while idx < len(self.simple_selectors):
                node = self.simple_selectors[idx]
                idx += 1

                if node.is_superset_of(other_node):
                    break

        return True

    def substitute(self, target, replacement):
        """Return a list of selectors obtained by replacing the `target`
        selector with `replacement`.

        Herein lie the guts of the Sass @extend directive.

        In general, for a selector ``a X b Y c``, a target ``X Y``, and a
        replacement ``q Z``, return the selectors ``a q X b Z c`` and ``q a X b
        Z c``.  Note in particular that no more than two selectors will be
        returned, and the permutation of ancestors will never insert new simple
        selectors "inside" the target selector.
        """

        # Find the target in the parent selector, and split it into
        # before/after
        p_before, p_extras, p_after = self.break_around(target.simple_selectors)

        # The replacement has no hinge; it only has the most specific simple
        # selector (which is the part that replaces "self" in the parent) and
        # whatever preceding simple selectors there may be
        r_trail = replacement.simple_selectors[:-1]
        r_extras = replacement.simple_selectors[-1]

        # TODO what if the prefix doesn't match?  who wins?  should we even get
        # this far?
        focal_nodes = (p_extras.merge_with(r_extras),)

        befores = _merge_selectors(p_before, r_trail)

        cls = type(self)
        return [
            cls(before + focal_nodes + p_after)
            for before in befores]

    def break_around(self, hinge):
        """Given a simple selector node contained within this one (a "hinge"),
        break it in half and return a parent selector, extra specifiers for the
        hinge, and a child selector.

        That is, given a hinge X, break the selector A + X.y B into A, + .y,
        and B.
        """
        hinge_start = hinge[0]
        for i, node in enumerate(self.simple_selectors):
            # In this particular case, a ' ' combinator actually means "no" (or
            # any) combinator, so it should be ignored
            if hinge_start.is_superset_of(node, soft_combinator=True):
                start_idx = i
                break
        else:
            raise ValueError(
                "Couldn't find hinge %r in compound selector %r" %
                (hinge_start, self.simple_selectors))

        for i, hinge_node in enumerate(hinge):
            if i == 0:
                # We just did this
                continue

            self_node = self.simple_selectors[start_idx + i]
            if hinge_node.is_superset_of(self_node):
                continue

            # TODO this isn't true; consider finding `a b` in `a c a b`
            raise ValueError(
                "Couldn't find hinge %r in compound selector %r" %
                (hinge_node, self.simple_selectors))

        end_idx = start_idx + len(hinge) - 1

        focal_node = self.simple_selectors[end_idx]
        extras = focal_node.difference(hinge[-1])

        return (
            self.simple_selectors[:start_idx],
            extras,
            self.simple_selectors[end_idx + 1:])

    def render(self):
        return ' '.join(simple.render() for simple in self.simple_selectors)


def _merge_selectors(left, right):
    """Given two selector chains (lists of simple selectors), return a list of
    selector chains representing elements matched by both of them.

    This operation is not exact, and involves some degree of fudging -- the
    wackier and more divergent the input, the more fudging.  It's meant to be
    what a human might expect rather than a precise covering of all possible
    cases.  Most notably, when the two input chains have absolutely nothing in
    common, the output is merely ``left + right`` and ``right + left`` rather
    than all possible interleavings.
    """

    if not left or not right:
        # At least one is empty, so there are no conflicts; just return
        # whichever isn't empty.  Remember to return a LIST, though
        return [left or right]

    lcs = longest_common_subsequence(left, right, _merge_simple_selectors)

    ret = [()]  # start with a dummy empty chain or weaving won't work

    left_last = 0
    right_last = 0
    for left_next, right_next, merged in lcs:
        ret = _weave_conflicting_selectors(
            ret,
            left[left_last:left_next],
            right[right_last:right_next],
            (merged,))

        left_last = left_next + 1
        right_last = right_next + 1

    ret = _weave_conflicting_selectors(
        ret,
        left[left_last:],
        right[right_last:])

    return ret


def _weave_conflicting_selectors(prefixes, a, b, suffix=()):
    """Part of the selector merge algorithm above.  Not useful on its own.  Pay
    no attention to the man behind the curtain.
    """
    # OK, what this actually does: given a list of selector chains, two
    # "conflicting" selector chains, and an optional suffix, return a new list
    # of chains like this:
    #   prefix[0] + a + b + suffix,
    #   prefix[0] + b + a + suffix,
    #   prefix[1] + a + b + suffix,
    #   ...
    # In other words, this just appends a new chain to each of a list of given
    # chains, except that the new chain might be the superposition of two
    # other incompatible chains.
    both = a and b
    for prefix in prefixes:
        yield prefix + a + b + suffix
        if both:
            # Only use both orderings if there's an actual conflict!
            yield prefix + b + a + suffix


def _merge_simple_selectors(a, b):
    """Merge two simple selectors, for the purposes of the LCS algorithm below.

    In practice this returns the more specific selector if one is a subset of
    the other, else it returns None.
    """
    # TODO what about combinators
    if a.is_superset_of(b):
        return b
    elif b.is_superset_of(a):
        return a
    else:
        return None


def longest_common_subsequence(a, b, mergefunc=None):
    """Find the longest common subsequence between two iterables.

    The longest common subsequence is the core of any diff algorithm: it's the
    longest sequence of elements that appears in both parent sequences in the
    same order, but NOT necessarily consecutively.

    Original algorithm borrowed from Wikipedia:
    http://en.wikipedia.org/wiki/Longest_common_subsequence_problem#Code_for_the_dynamic_programming_solution

    This function is used only to implement @extend, largely because that's
    what the Ruby implementation does.  Thus it's been extended slightly from
    the simple diff-friendly algorithm given above.

    What @extend wants to know is whether two simple selectors are compatible,
    not just equal.  To that end, you must pass in a "merge" function to
    compare a pair of elements manually.  It should return `None` if they are
    incompatible, and a MERGED element if they are compatible -- in the case of
    selectors, this is whichever one is more specific.

    Because of this fuzzier notion of equality, the return value is a list of
    ``(a_index, b_index, value)`` tuples rather than items alone.
    """
    if mergefunc is None:
        # Stupid default, just in case
        def mergefunc(a, b):
            if a == b:
                return a
            return None

    # Precalculate equality, since it can be a tad expensive and every pair is
    # compared at least once
    eq = {}
    for ai, aval in enumerate(a):
        for bi, bval in enumerate(b):
            eq[ai, bi] = mergefunc(aval, bval)

    # Build the "length" matrix, which provides the length of the LCS for
    # arbitrary-length prefixes.  -1 exists only to support the base case
    prefix_lcs_length = {}
    for ai in range(-1, len(a)):
        for bi in range(-1, len(b)):
            if ai == -1 or bi == -1:
                l = 0
            elif eq[ai, bi]:
                l = prefix_lcs_length[ai - 1, bi - 1] + 1
            else:
                l = max(
                    prefix_lcs_length[ai, bi - 1],
                    prefix_lcs_length[ai - 1, bi])

            prefix_lcs_length[ai, bi] = l

    # The interesting part.  The key insight is that the bottom-right value in
    # the length matrix must be the length of the LCS because of how the matrix
    # is defined, so all that's left to do is backtrack from the ends of both
    # sequences in whatever way keeps the LCS as long as possible, and keep
    # track of the equal pairs of elements we see along the way.
    # Wikipedia does this with recursion, but the algorithm is trivial to
    # rewrite as a loop, as below.
    ai = len(a) - 1
    bi = len(b) - 1

    ret = []
    while ai >= 0 and bi >= 0:
        merged = eq[ai, bi]
        if merged is not None:
            ret.append((ai, bi, merged))
            ai -= 1
            bi -= 1
        elif prefix_lcs_length[ai, bi - 1] > prefix_lcs_length[ai - 1, bi]:
            bi -= 1
        else:
            ai -= 1

    # ret has the latest items first, which is backwards
    ret.reverse()
    return ret
