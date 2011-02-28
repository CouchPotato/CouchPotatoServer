"""
Dictionnary classes which store values order.
"""

from hachoir_core.error import HachoirError
from hachoir_core.i18n import _

class UniqKeyError(HachoirError):
    """
    Error raised when a value is set whereas the key already exist in a
    dictionnary.
    """
    pass

class Dict(object):
    """
    This class works like classic Python dict() but has an important method:
    __iter__() which allow to iterate into the dictionnary _values_ (and not
    keys like Python's dict does).
    """
    def __init__(self, values=None):
        self._index = {}        # key => index
        self._key_list = []     # index => key
        self._value_list = []   # index => value
        if values:
            for key, value in values:
                self.append(key,value)

    def _getValues(self):
        return self._value_list
    values = property(_getValues)

    def index(self, key):
        """
        Search a value by its key and returns its index
        Returns None if the key doesn't exist.

        >>> d=Dict( (("two", "deux"), ("one", "un")) )
        >>> d.index("two")
        0
        >>> d.index("one")
        1
        >>> d.index("three") is None
        True
        """
        return self._index.get(key)

    def __getitem__(self, key):
        """
        Get item with specified key.
        To get a value by it's index, use mydict.values[index]

        >>> d=Dict( (("two", "deux"), ("one", "un")) )
        >>> d["one"]
        'un'
        """
        return self._value_list[self._index[key]]

    def __setitem__(self, key, value):
        self._value_list[self._index[key]] = value

    def append(self, key, value):
        """
        Append new value
        """
        if key in self._index:
            raise UniqKeyError(_("Key '%s' already exists") % key)
        self._index[key] = len(self._value_list)
        self._key_list.append(key)
        self._value_list.append(value)

    def __len__(self):
        return len(self._value_list)

    def __contains__(self, key):
        return key in self._index

    def __iter__(self):
        return iter(self._value_list)

    def iteritems(self):
        """
        Create a generator to iterate on: (key, value).

        >>> d=Dict( (("two", "deux"), ("one", "un")) )
        >>> for key, value in d.iteritems():
        ...    print "%r: %r" % (key, value)
        ...
        'two': 'deux'
        'one': 'un'
        """
        for index in xrange(len(self)):
            yield (self._key_list[index], self._value_list[index])

    def itervalues(self):
        """
        Create an iterator on values
        """
        return iter(self._value_list)

    def iterkeys(self):
        """
        Create an iterator on keys
        """
        return iter(self._key_list)

    def replace(self, oldkey, newkey, new_value):
        """
        Replace an existing value with another one

        >>> d=Dict( (("two", "deux"), ("one", "un")) )
        >>> d.replace("one", "three", 3)
        >>> d
        {'two': 'deux', 'three': 3}

        You can also use the classic form:

        >>> d['three'] = 4
        >>> d
        {'two': 'deux', 'three': 4}
        """
        index = self._index[oldkey]
        self._value_list[index] = new_value
        if oldkey != newkey:
            del self._index[oldkey]
            self._index[newkey] = index
            self._key_list[index] = newkey

    def __delitem__(self, index):
        """
        Delete item at position index. May raise IndexError.

        >>> d=Dict( ((6, 'six'), (9, 'neuf'), (4, 'quatre')) )
        >>> del d[1]
        >>> d
        {6: 'six', 4: 'quatre'}
        """
        if index < 0:
            index += len(self._value_list)
        if not (0 <= index < len(self._value_list)):
            raise IndexError(_("list assignment index out of range (%s/%s)")
                % (index, len(self._value_list)))
        del self._value_list[index]
        del self._key_list[index]

        # First loop which may alter self._index
        for key, item_index in self._index.iteritems():
            if item_index == index:
                del self._index[key]
                break

        # Second loop update indexes
        for key, item_index in self._index.iteritems():
            if index < item_index:
                self._index[key] -= 1

    def insert(self, index, key, value):
        """
        Insert an item at specified position index.

        >>> d=Dict( ((6, 'six'), (9, 'neuf'), (4, 'quatre')) )
        >>> d.insert(1, '40', 'quarante')
        >>> d
        {6: 'six', '40': 'quarante', 9: 'neuf', 4: 'quatre'}
        """
        if key in self:
            raise UniqKeyError(_("Insert error: key '%s' ready exists") % key)
        _index = index
        if index < 0:
            index += len(self._value_list)
        if not(0 <= index <= len(self._value_list)):
            raise IndexError(_("Insert error: index '%s' is invalid") % _index)
        for item_key, item_index in self._index.iteritems():
            if item_index >= index:
                self._index[item_key] += 1
        self._index[key] = index
        self._key_list.insert(index, key)
        self._value_list.insert(index, value)

    def __repr__(self):
        items = ( "%r: %r" % (key, value) for key, value in self.iteritems() )
        return "{%s}" % ", ".join(items)

