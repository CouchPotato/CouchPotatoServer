from hachoir_core.field import (MissingField, BasicFieldSet, Field, ParserError,
    createRawField, createNullField, createPaddingField, FakeArray)
from hachoir_core.dict import Dict, UniqKeyError
from hachoir_core.error import HACHOIR_ERRORS
from hachoir_core.tools import lowerBound
import hachoir_core.config as config

class GenericFieldSet(BasicFieldSet):
    """
    Ordered list of fields. Use operator [] to access fields using their
    name (field names are unique in a field set, but not in the whole
    document).

    Class attributes:
    - endian: Bytes order (L{BIG_ENDIAN} or L{LITTLE_ENDIAN}). Optional if the
      field set has a parent ;
    - static_size: (optional) Size of FieldSet in bits. This attribute should
      be used in parser of constant size.

    Instance attributes/methods:
    - _fields: Ordered dictionnary of all fields, may be incomplete
      because feeded when a field is requested ;
    - stream: Input stream used to feed fields' value
    - root: The root of all field sets ;
    - __len__(): Number of fields, may need to create field set ;
    - __getitem__(): Get an field by it's name or it's path.

    And attributes inherited from Field class:
    - parent: Parent field (may be None if it's the root) ;
    - name: Field name (unique in parent field set) ;
    - value: The field set ;
    - address: Field address (in bits) relative to parent ;
    - description: A string describing the content (can be None) ;
    - size: Size of field set in bits, may need to create field set.

    Event handling:
    - "connectEvent": Connect an handler to an event ;
    - "raiseEvent": Raise an event.

    To implement a new field set, you need to:
    - create a class which inherite from FieldSet ;
    - write createFields() method using lines like:
         yield Class(self, "name", ...) ;
    - and maybe set endian and static_size class attributes.
    """

    _current_size = 0

    def __init__(self, parent, name, stream, description=None, size=None):
        """
        Constructor
        @param parent: Parent field set, None for root parser
        @param name: Name of the field, have to be unique in parent. If it ends
            with "[]", end will be replaced with "[new_id]" (eg. "raw[]"
            becomes "raw[0]", next will be "raw[1]", and then "raw[2]", etc.)
        @type name: str
        @param stream: Input stream from which data are read
        @type stream: L{InputStream}
        @param description: Optional string description
        @type description: str|None
        @param size: Size in bits. If it's None, size will be computed. You
            can also set size with class attribute static_size
        """
        BasicFieldSet.__init__(self, parent, name, stream, description, size)
        self._fields = Dict()
        self._field_generator = self.createFields()
        self._array_cache = {}
        self.__is_feeding = False

    def array(self, key):
        try:
            return self._array_cache[key]
        except KeyError:
            array = FakeArray(self, key)
            self._array_cache[key] = array
            return self._array_cache[key]

    def reset(self):
        """
        Reset a field set:
         * clear fields ;
         * restart field generator ;
         * set current size to zero ;
         * clear field array count.

        But keep: name, value, description and size.
        """
        BasicFieldSet.reset(self)
        self._fields = Dict()
        self._field_generator = self.createFields()
        self._current_size = 0
        self._array_cache = {}

    def __str__(self):
        return '<%s path=%s, current_size=%s, current length=%s>' % \
            (self.__class__.__name__, self.path, self._current_size, len(self._fields))

    def __len__(self):
        """
        Returns number of fields, may need to create all fields
        if it's not done yet.
        """
        if self._field_generator is not None:
            self._feedAll()
        return len(self._fields)

    def _getCurrentLength(self):
        return len(self._fields)
    current_length = property(_getCurrentLength)

    def _getSize(self):
        if self._size is None:
            self._feedAll()
        return self._size
    size = property(_getSize, doc="Size in bits, may create all fields to get size")

    def _getCurrentSize(self):
        assert not(self.done)
        return self._current_size
    current_size = property(_getCurrentSize)

    eof = property(lambda self: self._checkSize(self._current_size + 1, True) < 0)

    def _checkSize(self, size, strict):
        field = self
        while field._size is None:
            if not field._parent:
                assert self.stream.size is None
                if not strict:
                    return None
                if self.stream.sizeGe(size):
                    return 0
                break
            size += field._address
            field = field._parent
        return field._size - size

    autofix = property(lambda self: self.root.autofix)

    def _addField(self, field):
        """
        Add a field to the field set:
        * add it into _fields
        * update _current_size

        May raise a StopIteration() on error
        """
        if not issubclass(field.__class__, Field):
            raise ParserError("Field type (%s) is not a subclass of 'Field'!"
                % field.__class__.__name__)
        assert isinstance(field._name, str)
        if field._name.endswith("[]"):
            self.setUniqueFieldName(field)
        if config.debug:
            self.info("[+] DBG: _addField(%s)" % field.name)

        # required for the msoffice parser
        if field._address != self._current_size:
            self.warning("Fix address of %s to %s (was %s)" %
                (field.path, self._current_size, field._address))
            field._address = self._current_size

        ask_stop = False
        # Compute field size and check that there is enough place for it
        self.__is_feeding = True
        try:
            field_size = field.size
        except HACHOIR_ERRORS, err:
            if field.is_field_set and field.current_length and field.eof:
                self.warning("Error when getting size of '%s': %s" % (field.name, err))
                field._stopFeeding()
                ask_stop = True
            else:
                self.warning("Error when getting size of '%s': delete it" % field.name)
                self.__is_feeding = False
                raise
        self.__is_feeding = False

        # No more place?
        dsize = self._checkSize(field._address + field.size, False)
        if (dsize is not None and dsize < 0) or (field.is_field_set and field.size <= 0):
            if self.autofix and self._current_size:
                self._fixFieldSize(field, field.size + dsize)
            else:
                raise ParserError("Field %s is too large!" % field.path)

        self._current_size += field.size
        try:
            self._fields.append(field._name, field)
        except UniqKeyError, err:
            self.warning("Duplicate field name " + unicode(err))
            field._name += "[]"
            self.setUniqueFieldName(field)
            self._fields.append(field._name, field)
        if ask_stop:
            raise StopIteration()

    def _fixFieldSize(self, field, new_size):
        if new_size > 0:
            if field.is_field_set and 0 < field.size:
                field._truncate(new_size)
                return

            # Don't add the field <=> delete item
            if self._size is None:
                self._size = self._current_size + new_size
        self.warning("[Autofix] Delete '%s' (too large)" % field.path)
        raise StopIteration()

    def _getField(self, name, const):
        field = Field._getField(self, name, const)
        if field is None:
            if name in self._fields:
                field = self._fields[name]
            elif self._field_generator is not None and not const:
                field = self._feedUntil(name)
        return field

    def getField(self, key, const=True):
        if isinstance(key, (int, long)):
            if key < 0:
                raise KeyError("Key must be positive!")
            if not const:
                self.readFirstFields(key+1)
            if len(self._fields.values) <= key:
                raise MissingField(self, key)
            return self._fields.values[key]
        return Field.getField(self, key, const)

    def _truncate(self, size):
        assert size > 0
        if size < self._current_size:
            self._size = size
            while True:
                field = self._fields.values[-1]
                if field._address < size:
                    break
                del self._fields[-1]
            self._current_size = field._address
            size -= field._address
            if size < field._size:
                if field.is_field_set:
                    field._truncate(size)
                else:
                    del self._fields[-1]
                    field = createRawField(self, size, "raw[]")
                    self._fields.append(field._name, field)
            self._current_size = self._size
        else:
            assert size < self._size or self._size is None
            self._size = size
        if self._size == self._current_size:
            self._field_generator = None

    def _deleteField(self, index):
        field = self._fields.values[index]
        size = field.size
        self._current_size -= size
        del self._fields[index]
        return field

    def _fixLastField(self):
        """
        Try to fix last field when we know current field set size.
        Returns new added field if any, or None.
        """
        assert self._size is not None

        # Stop parser
        message = ["stop parser"]
        self._field_generator = None

        # If last field is too big, delete it
        while self._size < self._current_size:
            field = self._deleteField(len(self._fields)-1)
            message.append("delete field %s" % field.path)
        assert self._current_size <= self._size

        # If field size current is smaller: add a raw field
        size = self._size - self._current_size
        if size:
            field = createRawField(self, size, "raw[]")
            message.append("add padding")
            self._current_size += field.size
            self._fields.append(field._name, field)
        else:
            field = None
        message = ", ".join(message)
        self.warning("[Autofix] Fix parser error: " + message)
        assert self._current_size == self._size
        return field

    def _stopFeeding(self):
        new_field = None
        if self._size is None:
            if self._parent:
                self._size = self._current_size
        elif self._size != self._current_size:
            if self.autofix:
                new_field = self._fixLastField()
            else:
                raise ParserError("Invalid parser \"%s\" size!" % self.path)
        self._field_generator = None
        return new_field

    def _fixFeedError(self, exception):
        """
        Try to fix a feeding error. Returns False if error can't be fixed,
        otherwise returns new field if any, or None.
        """
        if self._size is None or not self.autofix:
            return False
        self.warning(unicode(exception))
        return self._fixLastField()

    def _feedUntil(self, field_name):
        """
        Return the field if it was found, None else
        """
        if self.__is_feeding \
        or (self._field_generator and self._field_generator.gi_running):
            self.warning("Unable to get %s (and generator is already running)"
                % field_name)
            return None
        try:
            while True:
                field = self._field_generator.next()
                self._addField(field)
                if field.name == field_name:
                    return field
        except HACHOIR_ERRORS, err:
            if self._fixFeedError(err) is False:
                raise
        except StopIteration:
            self._stopFeeding()
        return None

    def readMoreFields(self, number):
        """
        Read more number fields, or do nothing if parsing is done.

        Returns number of new added fields.
        """
        if self._field_generator is None:
            return 0
        oldlen = len(self._fields)
        try:
            for index in xrange(number):
                self._addField( self._field_generator.next() )
        except HACHOIR_ERRORS, err:
            if self._fixFeedError(err) is False:
                raise
        except StopIteration:
            self._stopFeeding()
        return len(self._fields) - oldlen

    def _feedAll(self):
        if self._field_generator is None:
            return
        try:
            while True:
                field = self._field_generator.next()
                self._addField(field)
        except HACHOIR_ERRORS, err:
            if self._fixFeedError(err) is False:
                raise
        except StopIteration:
            self._stopFeeding()

    def __iter__(self):
        """
        Create a generator to iterate on each field, may create new
        fields when needed
        """
        try:
            done = 0
            while True:
                if done == len(self._fields):
                    if self._field_generator is None:
                        break
                    self._addField( self._field_generator.next() )
                for field in self._fields.values[done:]:
                    yield field
                    done += 1
        except HACHOIR_ERRORS, err:
            field = self._fixFeedError(err)
            if isinstance(field, Field):
                yield field
            elif hasattr(field, '__iter__'):
                for f in field:
                    yield f
            elif field is False:
                raise
        except StopIteration:
            field = self._stopFeeding()
            if isinstance(field, Field):
                yield field
            elif hasattr(field, '__iter__'):
                for f in field:
                    yield f

    def _isDone(self):
        return (self._field_generator is None)
    done = property(_isDone, doc="Boolean to know if parsing is done or not")

    #
    # FieldSet_SeekUtility
    #
    def seekBit(self, address, name="padding[]",
    description=None, relative=True, null=False):
        """
        Create a field to seek to specified address,
        or None if it's not needed.

        May raise an (ParserError) exception if address is invalid.
        """
        if relative:
            nbits = address - self._current_size
        else:
            nbits = address - (self.absolute_address + self._current_size)
        if nbits < 0:
            raise ParserError("Seek error, unable to go back!")
        if 0 < nbits:
            if null:
                return createNullField(self, nbits, name, description)
            else:
                return createPaddingField(self, nbits, name, description)
        else:
            return None

    def seekByte(self, address, name="padding[]", description=None, relative=True, null=False):
        """
        Same as seekBit(), but with address in byte.
        """
        return self.seekBit(address * 8, name, description, relative, null=null)

    #
    # RandomAccessFieldSet
    #
    def replaceField(self, name, new_fields):
        # TODO: Check in self and not self.field
        # Problem is that "generator is already executing"
        if name not in self._fields:
            raise ParserError("Unable to replace %s: field doesn't exist!" % name)
        assert 1 <= len(new_fields)
        old_field = self[name]
        total_size = sum( (field.size for field in new_fields) )
        if old_field.size != total_size:
            raise ParserError("Unable to replace %s: "
                "new field(s) hasn't same size (%u bits instead of %u bits)!"
                % (name, total_size, old_field.size))
        field = new_fields[0]
        if field._name.endswith("[]"):
            self.setUniqueFieldName(field)
        field._address = old_field.address
        if field.name != name and field.name in self._fields:
            raise ParserError(
                "Unable to replace %s: name \"%s\" is already used!"
                % (name, field.name))
        self._fields.replace(name, field.name, field)
        self.raiseEvent("field-replaced", old_field, field)
        if 1 < len(new_fields):
            index = self._fields.index(new_fields[0].name)+1
            address = field.address + field.size
            for field in new_fields[1:]:
                if field._name.endswith("[]"):
                    self.setUniqueFieldName(field)
                field._address = address
                if field.name in self._fields:
                    raise ParserError(
                        "Unable to replace %s: name \"%s\" is already used!"
                        % (name, field.name))
                self._fields.insert(index, field.name, field)
                self.raiseEvent("field-inserted", index, field)
                index += 1
                address += field.size

    def getFieldByAddress(self, address, feed=True):
        """
        Only search in existing fields
        """
        if feed and self._field_generator is not None:
            self._feedAll()
        if address < self._current_size:
            i = lowerBound(self._fields.values, lambda x: x.address + x.size <= address)
            if i is not None:
                return self._fields.values[i]
        return None

    def writeFieldsIn(self, old_field, address, new_fields):
        """
        Can only write in existing fields (address < self._current_size)
        """

        # Check size
        total_size = sum( field.size for field in new_fields )
        if old_field.size < total_size:
            raise ParserError( \
                "Unable to write fields at address %s " \
                "(too big)!" % (address))

        # Need padding before?
        replace = []
        size = address - old_field.address
        assert 0 <= size
        if 0 < size:
            padding = createPaddingField(self, size)
            padding._address = old_field.address
            replace.append(padding)

        # Set fields address
        for field in new_fields:
            field._address = address
            address += field.size
            replace.append(field)

        # Need padding after?
        size = (old_field.address + old_field.size) - address
        assert 0 <= size
        if 0 < size:
            padding = createPaddingField(self, size)
            padding._address = address
            replace.append(padding)

        self.replaceField(old_field.name, replace)

    def nextFieldAddress(self):
        return self._current_size

    def getFieldIndex(self, field):
        return self._fields.index(field._name)

