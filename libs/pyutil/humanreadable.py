#  Copyright (c) 2001 Autonomous Zone Industries
#  Copyright (c) 2002-2009 Zooko "Zooko" Wilcox-O'Hearn
#  This file is part of pyutil; see README.rst for licensing terms.

import exceptions, os
from repr import Repr

class BetterRepr(Repr):
    def __init__(self):
        Repr.__init__(self)

        # Note: These levels can get adjusted dynamically!  My goal is to get more info when printing important debug stuff like exceptions and stack traces and less info when logging normal events.  --Zooko 2000-10-14
        self.maxlevel = 6
        self.maxdict = 6
        self.maxlist = 6
        self.maxtuple = 6
        self.maxstring = 300
        self.maxother = 300

    def repr_function(self, obj, level):
        if hasattr(obj, 'func_code'):
            return '<' + obj.func_name + '() at ' + os.path.basename(obj.func_code.co_filename) + ':' + str(obj.func_code.co_firstlineno) + '>'
        else:
            return '<' + obj.func_name + '() at (builtin)'

    def repr_instance_method(self, obj, level):
        if hasattr(obj, 'func_code'):
            return '<' + obj.im_class.__name__ + '.' + obj.im_func.__name__ + '() at ' + os.path.basename(obj.im_func.func_code.co_filename) + ':' + str(obj.im_func.func_code.co_firstlineno) + '>'
        else:
            return '<' + obj.im_class.__name__ + '.' + obj.im_func.__name__ + '() at (builtin)'

    def repr_long(self, obj, level):
        s = `obj` # XXX Hope this isn't too slow...
        if len(s) > self.maxlong:
            i = max(0, (self.maxlong-3)/2)
            j = max(0, self.maxlong-3-i)
            s = s[:i] + '...' + s[len(s)-j:]
        if s[-1] == 'L':
            return s[:-1]
        return s

    def repr_instance(self, obj, level):
        """
        If it is an instance of Exception, format it nicely (trying to emulate
        the format that you see when an exception is actually raised, plus
        bracketing '<''s).  If it is an instance of dict call self.repr_dict()
        on it.  If it is an instance of list call self.repr_list() on it. Else
        call Repr.repr_instance().
        """
        if isinstance(obj, exceptions.Exception):
            # Don't cut down exception strings so much.
            tms = self.maxstring
            self.maxstring = max(512, tms * 4)
            tml = self.maxlist
            self.maxlist = max(12, tml * 4)
            try:
                if hasattr(obj, 'args'):
                    if len(obj.args) == 1:
                        return '<' + obj.__class__.__name__ + ': ' + self.repr1(obj.args[0], level-1) + '>'
                    else:
                        return '<' + obj.__class__.__name__ + ': ' + self.repr1(obj.args, level-1) + '>'
                else:
                    return '<' + obj.__class__.__name__ + '>'
            finally:
                self.maxstring = tms
                self.maxlist = tml

        if isinstance(obj, dict):
            return self.repr_dict(obj, level)

        if isinstance(obj, list):
            return self.repr_list(obj, level)

        return Repr.repr_instance(self, obj, level)

    def repr_list(self, obj, level):
        """
        copied from standard repr.py and fixed to work on multithreadedly mutating lists.
        """
        if level <= 0: return '[...]'
        n = len(obj)
        myl = obj[:min(n, self.maxlist)]
        s = ''
        for item in myl:
            entry = self.repr1(item, level-1)
            if s: s = s + ', '
            s = s + entry
        if n > self.maxlist: s = s + ', ...'
        return '[' + s + ']'

    def repr_dict(self, obj, level):
        """
        copied from standard repr.py and fixed to work on multithreadedly mutating dicts.
        """
        if level <= 0: return '{...}'
        s = ''
        n = len(obj)
        items = obj.items()[:min(n, self.maxdict)]
        items.sort()
        for key, val in items:
            entry = self.repr1(key, level-1) + ':' + self.repr1(val, level-1)
            if s: s = s + ', '
            s = s + entry
        if n > self.maxdict: s = s + ', ...'
        return '{' + s + '}'

# This object can be changed by other code updating this module's "brepr"
# variables.  This is so that (a) code can use humanreadable with
# "from humanreadable import hr; hr(mything)", and (b) code can override
# humanreadable to provide application-specific human readable output
# (e.g. libbase32's base32id.AbbrevRepr).
brepr = BetterRepr()

def hr(x):
    return brepr.repr(x)
