from hachoir_core.field import Field, FieldSet, ParserError, Bytes, MissingField
from hachoir_core.stream import FragmentedStream


class Link(Field):
    def __init__(self, parent, name, *args, **kw):
        Field.__init__(self, parent, name, 0, *args, **kw)

    def hasValue(self):
        return True

    def createValue(self):
        return self._parent[self.display]

    def createDisplay(self):
        value = self.value
        if value is None:
            return "<%s>" % MissingField.__name__
        return value.path

    def _getField(self, name, const):
        target = self.value
        assert self != target
        return target._getField(name, const)


class Fragments:
    def __init__(self, first):
        self.first = first

    def __iter__(self):
        fragment = self.first
        while fragment is not None:
            data = fragment.getData()
            yield data and data.size
            fragment = fragment.next


class Fragment(FieldSet):
    _first = None

    def __init__(self, *args, **kw):
        FieldSet.__init__(self, *args, **kw)
        self._field_generator = self._createFields(self._field_generator)
        if self.__class__.createFields == Fragment.createFields:
            self._getData = lambda: self

    def getData(self):
        try:
            return self._getData()
        except MissingField, e:
            self.error(str(e))
        return None

    def setLinks(self, first, next=None):
        self._first = first or self
        self._next = next
        self._feedLinks = lambda: self
        return self

    def _feedLinks(self):
        while self._first is None and self.readMoreFields(1):
            pass
        if self._first is None:
            raise ParserError("first is None")
        return self
    first = property(lambda self: self._feedLinks()._first)

    def _getNext(self):
        next = self._feedLinks()._next
        if callable(next):
            self._next = next = next()
        return next
    next  = property(_getNext)

    def _createInputStream(self, **args):
        first = self.first
        if first is self and hasattr(first, "_getData"):
            return FragmentedStream(first, packets=Fragments(first), **args)
        return FieldSet._createInputStream(self, **args)

    def _createFields(self, field_generator):
        if self._first is None:
            for field in field_generator:
                if self._first is not None:
                    break
                yield field
            else:
                raise ParserError("Fragment.setLinks not called")
        else:
            field = None
        if self._first is not self:
            link = Link(self, "first", None)
            link._getValue = lambda: self._first
            yield link
        if self._next:
            link = Link(self, "next", None)
            link.createValue = self._getNext
            yield link
        if field:
            yield field
        for field in field_generator:
            yield field

    def createFields(self):
        if self._size is None:
            self._size = self._getSize()
        yield Bytes(self, "data", self._size/8)

