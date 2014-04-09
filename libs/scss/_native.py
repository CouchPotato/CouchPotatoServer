"""Pure-Python scanner and parser, used if _speedups is not available."""
from __future__ import print_function

from scss.cssdefs import SEPARATOR
import re

DEBUG = False

# TODO copied from __init__
_nl_num_re = re.compile(r'\n.+' + SEPARATOR, re.MULTILINE)
_blocks_re = re.compile(r'[{},;()\'"\n]')


def _strip_selprop(selprop, lineno):
    # Get the line number of the selector or property and strip all other
    # line numbers that might still be there (from multiline selectors)
    _lineno, _sep, selprop = selprop.partition(SEPARATOR)
    if _sep == SEPARATOR:
        _lineno = _lineno.strip(' \t\n;')
        try:
            lineno = int(_lineno)
        except ValueError:
            pass
    else:
        selprop = _lineno
    selprop = _nl_num_re.sub('\n', selprop)
    selprop = selprop.strip()
    return selprop, lineno


def _strip(selprop):
    # Strip all line numbers, ignoring them in the way
    selprop, _ = _strip_selprop(selprop, None)
    return selprop


def locate_blocks(codestr):
    """
    For processing CSS like strings.

    Either returns all selectors (that can be "smart" multi-lined, as
    long as it's joined by `,`, or enclosed in `(` and `)`) with its code block
    (the one between `{` and `}`, which can be nested), or the "lose" code
    (properties) that doesn't have any blocks.
    """
    lineno = 0

    par = 0
    instr = None
    depth = 0
    skip = False
    thin = None
    i = init = safe = lose = 0
    start = end = None

    for m in _blocks_re.finditer(codestr):
        i = m.start(0)
        c = codestr[i]
        if instr is not None:
            if c == instr:
                instr = None  # A string ends (FIXME: needs to accept escaped characters)
        elif c in ('"', "'"):
            instr = c  # A string starts
        elif c == '(':  # parenthesis begins:
            par += 1
            thin = None
            safe = i + 1
        elif c == ')':  # parenthesis ends:
            par -= 1
        elif not par and not instr:
            if c == '{':  # block begins:
                if depth == 0:
                    if i > 0 and codestr[i - 1] == '#':  # Do not process #{...} as blocks!
                        skip = True
                    else:
                        start = i
                        if thin is not None and _strip(codestr[thin:i]):
                            init = thin
                        if lose < init:
                            _property, lineno = _strip_selprop(codestr[lose:init], lineno)
                            if _property:
                                yield lineno, _property, None
                            lose = init
                        thin = None
                depth += 1
            elif c == '}':  # block ends:
                if depth > 0:
                    depth -= 1
                    if depth == 0:
                        if not skip:
                            end = i
                            _selectors, lineno = _strip_selprop(codestr[init:start], lineno)
                            _codestr = codestr[start + 1:end].strip()
                            if _selectors:
                                yield lineno, _selectors, _codestr
                            init = safe = lose = end + 1
                            thin = None
                        skip = False
            elif depth == 0:
                if c == ';':  # End of property (or block):
                    init = i
                    if lose < init:
                        _property, lineno = _strip_selprop(codestr[lose:init], lineno)
                        if _property:
                            yield lineno, _property, None
                        init = safe = lose = i + 1
                    thin = None
                elif c == ',':
                    if thin is not None and _strip(codestr[thin:i]):
                        init = thin
                    thin = None
                    safe = i + 1
                elif c == '\n':
                    if thin is not None and _strip(codestr[thin:i]):
                        init = thin
                        thin = i + 1
                    elif thin is None and _strip(codestr[safe:i]):
                        thin = i + 1  # Step on thin ice, if it breaks, it breaks here
    if depth > 0:
        if not skip:
            _selectors, lineno = _strip_selprop(codestr[init:start], lineno)
            _codestr = codestr[start + 1:].strip()
            if _selectors:
                yield lineno, _selectors, _codestr
            if par:
                raise Exception("Missing closing parenthesis somewhere in block: '%s'" % _selectors)
            elif instr:
                raise Exception("Missing closing string somewhere in block: '%s'" % _selectors)
            else:
                raise Exception("Block never closed: '%s'" % _selectors)
    losestr = codestr[lose:]
    for _property in losestr.split(';'):
        _property, lineno = _strip_selprop(_property, lineno)
        if _property:
            yield lineno, _property, None


################################################################################
# Parser

class NoMoreTokens(Exception):
    """
    Another exception object, for when we run out of tokens
    """
    pass


class Scanner(object):
    def __init__(self, patterns, ignore, input=None):
        """
        Patterns is [(terminal,regex)...]
        Ignore is [terminal,...];
        Input is a string
        """
        self.reset(input)
        self.ignore = ignore
        # The stored patterns are a pair (compiled regex,source
        # regex).  If the patterns variable passed in to the
        # constructor is None, we assume that the class already has a
        # proper .patterns list constructed
        if patterns is not None:
            self.patterns = []
            for k, r in patterns:
                self.patterns.append((k, re.compile(r)))

    def reset(self, input):
        self.tokens = []
        self.restrictions = []
        self.input = input
        self.pos = 0

    def __repr__(self):
        """
        Print the last 10 tokens that have been scanned in
        """
        output = ''
        for t in self.tokens[-10:]:
            output = "%s\n  (@%s)  %s  =  %s" % (output, t[0], t[2], repr(t[3]))
        return output

    def _scan(self, restrict):
        """
        Should scan another token and add it to the list, self.tokens,
        and add the restriction to self.restrictions
        """
        # Keep looking for a token, ignoring any in self.ignore
        token = None
        while True:
            best_pat = None
            # Search the patterns for a match, with earlier
            # tokens in the list having preference
            best_pat_len = 0
            for tok, regex in self.patterns:
                if DEBUG:
                    print("\tTrying %s: %s at pos %d -> %s" % (repr(tok), repr(regex.pattern), self.pos, repr(self.input)))
                # First check to see if we're restricting to this token
                if restrict and tok not in restrict and tok not in self.ignore:
                    if DEBUG:
                        print("\tSkipping %r!" % (tok,))
                    continue
                m = regex.match(self.input, self.pos)
                if m:
                    # We got a match
                    best_pat = tok
                    best_pat_len = len(m.group(0))
                    if DEBUG:
                        print("Match OK! %s: %s at pos %d" % (repr(tok), repr(regex.pattern), self.pos))
                    break

            # If we didn't find anything, raise an error
            if best_pat is None:
                msg = "Bad token found"
                if restrict:
                    msg = "Bad token found while trying to find one of the restricted tokens: %s" % (", ".join(repr(r) for r in restrict))
                raise SyntaxError("SyntaxError[@ char %s: %s]" % (repr(self.pos), msg))

            # If we found something that isn't to be ignored, return it
            if best_pat in self.ignore:
                # This token should be ignored...
                self.pos += best_pat_len
            else:
                end_pos = self.pos + best_pat_len
                # Create a token with this data
                token = (
                    self.pos,
                    end_pos,
                    best_pat,
                    self.input[self.pos:end_pos]
                )
                break
        if token is not None:
            self.pos = token[1]
            # Only add this token if it's not in the list
            # (to prevent looping)
            if not self.tokens or token != self.tokens[-1]:
                self.tokens.append(token)
                self.restrictions.append(restrict)
                return 1
        return 0

    def token(self, i, restrict=None):
        """
        Get the i'th token, and if i is one past the end, then scan
        for another token; restrict is a list of tokens that
        are allowed, or 0 for any token.
        """
        tokens_len = len(self.tokens)
        if i == tokens_len:  # We are at the end, get the next...
            tokens_len += self._scan(restrict)
        if i < tokens_len:
            if restrict and self.restrictions[i] and restrict > self.restrictions[i]:
                raise NotImplementedError("Unimplemented: restriction set changed")
            return self.tokens[i]
        raise NoMoreTokens

    def rewind(self, i):
        tokens_len = len(self.tokens)
        if i <= tokens_len:
            token = self.tokens[i]
            self.tokens = self.tokens[:i]
            self.restrictions = self.restrictions[:i]
            self.pos = token[0]
