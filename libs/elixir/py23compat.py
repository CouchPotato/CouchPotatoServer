# Some helper functions to get by without Python 2.4

# set
try:
    set = set
except NameError:
    from sets import Set as set

orig_cmp = cmp
# [].sort
def sort_list(l, cmp=None, key=None, reverse=False):
    try:
        l.sort(cmp, key, reverse)
    except TypeError, e:
        if not str(e).startswith('sort expected at most 1 arguments'):
            raise
        if cmp is None:
            cmp = orig_cmp
        if key is not None:
            # the cmp=cmp parameter is required to get the original comparator
            # into the lambda namespace
            cmp = lambda self, other, cmp=cmp: cmp(key(self), key(other))
        if reverse:
            cmp = lambda self, other, cmp=cmp: -cmp(self,other)
        l.sort(cmp)

# sorted
try:
    sorted = sorted
except NameError:
    # global name 'sorted' doesn't exist in Python2.3
    # this provides a poor-man's emulation of the sorted built-in method
    def sorted(l, cmp=None, key=None, reverse=False):
        sorted_list = list(l)
        sort_list(sorted_list, cmp, key, reverse)
        return sorted_list

# rsplit
try:
    ''.rsplit
    def rsplit(s, delim, maxsplit):
        return s.rsplit(delim, maxsplit)

except AttributeError:
    def rsplit(s, delim, maxsplit):
        """Return a list of the words of the string s, scanning s
        from the end. To all intents and purposes, the resulting
        list of words is the same as returned by split(), except
        when the optional third argument maxsplit is explicitly
        specified and nonzero. When maxsplit is nonzero, at most
        maxsplit number of splits - the rightmost ones - occur,
        and the remainder of the string is returned as the first
        element of the list (thus, the list will have at most
        maxsplit+1 elements). New in version 2.4.
        >>> rsplit('foo.bar.baz', '.', 0)
        ['foo.bar.baz']
        >>> rsplit('foo.bar.baz', '.', 1)
        ['foo.bar', 'baz']
        >>> rsplit('foo.bar.baz', '.', 2)
        ['foo', 'bar', 'baz']
        >>> rsplit('foo.bar.baz', '.', 99)
        ['foo', 'bar', 'baz']
        """
        assert maxsplit >= 0

        if maxsplit == 0: return [s]

        # the following lines perform the function, but inefficiently.
        #  This may be adequate for compatibility purposes
        items = s.split(delim)
        if maxsplit < len(items):
            items[:-maxsplit] = [delim.join(items[:-maxsplit])]
        return items
