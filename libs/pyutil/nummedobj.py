# Copyright (c) 2002-2009 Zooko Wilcox-O'Hearn
# mailto:zooko@zooko.com
#  This file is part of pyutil; see README.rst for licensing terms.

import dictutil

class NummedObj(object):
    """
    This is useful for nicer debug printouts.  Instead of objects of the same class being
    distinguished from one another by their memory address, they each get a unique number, which
    can be read as "the first object of this class", "the second object of this class", etc.  This
    is especially useful because separate runs of a program will yield identical debug output,
    (assuming that the objects get created in the same order in each run).  This makes it possible
    to diff outputs from separate runs to see what changed, without having to ignore a difference
    on every line due to different memory addresses of objects.
    """
    objnums = dictutil.NumDict() # key: class names, value: highest used object number

    def __init__(self, klass=None):
        """
        @param klass: in which class are you counted?  If default value of `None', then self.__class__ will be used.
        """
        if klass is None:
            klass = self.__class__
        self._classname = klass.__name__
            
        NummedObj.objnums.inc(self._classname)
        self._objid = NummedObj.objnums[self._classname]

    def __repr__(self):
        return "<%s #%d>" % (self._classname, self._objid,)

    def __lt__(self, other):
        return (self._objid, self._classname,) < (other._objid, other._classname,)

    def __le__(self, other):
        return (self._objid, self._classname,) <= (other._objid, other._classname,)

    def __eq__(self, other):
        return (self._objid, self._classname,) == (other._objid, other._classname,)

    def __ne__(self, other):
        return (self._objid, self._classname,) != (other._objid, other._classname,)

    def __gt__(self, other):
        return (self._objid, self._classname,) > (other._objid, other._classname,)

    def __ge__(self, other):
        return (self._objid, self._classname,) >= (other._objid, other._classname,)

    def __hash__(self):
        return id(self)
