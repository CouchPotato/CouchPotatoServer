from hachoir_core.field import Field, BasicFieldSet, FakeArray, MissingField, ParserError
from hachoir_core.tools import makeUnicode
from hachoir_core.error import HACHOIR_ERRORS
from itertools import repeat
import hachoir_core.config as config

class RootSeekableFieldSet(BasicFieldSet):
    def __init__(self, parent, name, stream, description, size):
        BasicFieldSet.__init__(self, parent, name, stream, description, size)
        self._generator = self.createFields()
        self._offset = 0
        self._current_size = 0
        if size:
            self._current_max_size = size
        else:
            self._current_max_size = 0
        self._field_dict = {}
        self._field_array = []

    def _feedOne(self):
        assert self._generator
        field = self._generator.next()
        self._addField(field)
        return field

    def array(self, key):
        return FakeArray(self, key)

    def getFieldByAddress(self, address, feed=True):
        for field in self._field_array:
            if field.address <= address < field.address + field.size:
                return field
        for field in self._readFields():
            if field.address <= address < field.address + field.size:
                return field
        return None

    def _stopFeed(self):
        self._size = self._current_max_size
        self._generator = None
    done = property(lambda self: not bool(self._generator))

    def _getSize(self):
        if self._size is None:
            self._feedAll()
        return self._size
    size = property(_getSize)

    def _getField(self, key, const):
        field = Field._getField(self, key, const)
        if field is not None:
            return field
        if key in self._field_dict:
            return self._field_dict[key]
        if self._generator and not const:
            try:
                while True:
                    field = self._feedOne()
                    if field.name == key:
                        return field
            except StopIteration:
                self._stopFeed()
            except HACHOIR_ERRORS, err:
                self.error("Error: %s" % makeUnicode(err))
                self._stopFeed()
        return None

    def getField(self, key, const=True):
        if isinstance(key, (int, long)):
            if key < 0:
                raise KeyError("Key must be positive!")
            if not const:
                self.readFirstFields(key+1)
            if len(self._field_array) <= key:
                raise MissingField(self, key)
            return self._field_array[key]
        return Field.getField(self, key, const)

    def _addField(self, field):
        if field._name.endswith("[]"):
            self.setUniqueFieldName(field)
        if config.debug:
            self.info("[+] DBG: _addField(%s)" % field.name)

        if field._address != self._offset:
            self.warning("Set field %s address to %s (was %s)" % (
                field.path, self._offset//8, field._address//8))
            field._address = self._offset
        assert field.name not in self._field_dict

        self._checkFieldSize(field)

        self._field_dict[field.name] = field
        self._field_array.append(field)
        self._current_size += field.size
        self._offset += field.size
        self._current_max_size = max(self._current_max_size, field.address + field.size)

    def _checkAddress(self, address):
        if self._size is not None:
            max_addr = self._size
        else:
            # FIXME: Use parent size
            max_addr = self.stream.size
        return address < max_addr

    def _checkFieldSize(self, field):
        size = field.size
        addr = field.address
        if not self._checkAddress(addr+size-1):
            raise ParserError("Unable to add %s: field is too large" % field.name)

    def seekBit(self, address, relative=True):
        if not relative:
            address -= self.absolute_address
        if address < 0:
            raise ParserError("Seek below field set start (%s.%s)" % divmod(address, 8))
        if not self._checkAddress(address):
            raise ParserError("Seek above field set end (%s.%s)" % divmod(address, 8))
        self._offset = address
        return None

    def seekByte(self, address, relative=True):
        return self.seekBit(address*8, relative)

    def readMoreFields(self, number):
        return self._readMoreFields(xrange(number))

    def _feedAll(self):
        return self._readMoreFields(repeat(1))

    def _readFields(self):
        while True:
            added = self._readMoreFields(xrange(1))
            if not added:
                break
            yield self._field_array[-1]

    def _readMoreFields(self, index_generator):
        added = 0
        if self._generator:
            try:
                for index in index_generator:
                    self._feedOne()
                    added += 1
            except StopIteration:
                self._stopFeed()
            except HACHOIR_ERRORS, err:
                self.error("Error: %s" % makeUnicode(err))
                self._stopFeed()
        return added

    current_length = property(lambda self: len(self._field_array))
    current_size = property(lambda self: self._offset)

    def __iter__(self):
        for field in self._field_array:
            yield field
        if self._generator:
            try:
                while True:
                    yield self._feedOne()
            except StopIteration:
                self._stopFeed()
                raise StopIteration

    def __len__(self):
        if self._generator:
            self._feedAll()
        return len(self._field_array)

    def nextFieldAddress(self):
        return self._offset

    def getFieldIndex(self, field):
        return self._field_array.index(field)

class SeekableFieldSet(RootSeekableFieldSet):
    def __init__(self, parent, name, description=None, size=None):
        assert issubclass(parent.__class__, BasicFieldSet)
        RootSeekableFieldSet.__init__(self, parent, name, parent.stream, description, size)

