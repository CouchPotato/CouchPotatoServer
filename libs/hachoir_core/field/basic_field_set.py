from hachoir_core.field import Field, FieldError
from hachoir_core.stream import InputStream
from hachoir_core.endian import BIG_ENDIAN, LITTLE_ENDIAN
from hachoir_core.event_handler import EventHandler

class ParserError(FieldError):
    """
    Error raised by a field set.

    @see: L{FieldError}
    """
    pass

class MatchError(FieldError):
    """
    Error raised by a field set when the stream content doesn't
    match to file format.

    @see: L{FieldError}
    """
    pass

class BasicFieldSet(Field):
    _event_handler = None
    is_field_set = True
    endian = None

    def __init__(self, parent, name, stream, description, size):
        # Sanity checks (preconditions)
        assert not parent or issubclass(parent.__class__, BasicFieldSet)
        assert issubclass(stream.__class__, InputStream)

        # Set field set size
        if size is None and self.static_size:
            assert isinstance(self.static_size, (int, long))
            size = self.static_size

        # Set Field attributes
        self._parent = parent
        self._name = name
        self._size = size
        self._description = description
        self.stream = stream
        self._field_array_count = {}

        # Set endian
        if not self.endian:
            assert parent and parent.endian
            self.endian = parent.endian

        if parent:
            # This field set is one of the root leafs
            self._address = parent.nextFieldAddress()
            self.root = parent.root
            assert id(self.stream) == id(parent.stream)
        else:
            # This field set is the root
            self._address = 0
            self.root = self
            self._global_event_handler = None

        # Sanity checks (post-conditions)
        assert self.endian in (BIG_ENDIAN, LITTLE_ENDIAN)
        if (self._size is not None) and (self._size <= 0):
            raise ParserError("Invalid parser '%s' size: %s" % (self.path, self._size))

    def reset(self):
        self._field_array_count = {}

    def createValue(self):
        return None

    def connectEvent(self, event_name, handler, local=True):
        assert event_name in (
            # Callback prototype: def f(field)
            # Called when new value is already set
            "field-value-changed",

            # Callback prototype: def f(field)
            # Called when field size is already set
            "field-resized",

            # A new field has been inserted in the field set
            # Callback prototype: def f(index, new_field)
            "field-inserted",

            # Callback prototype: def f(old_field, new_field)
            # Called when new field is already in field set
            "field-replaced",

            # Callback prototype: def f(field, new_value)
            # Called to ask to set new value
            "set-field-value"
        ), "Event name %r is invalid" % event_name
        if local:
            if self._event_handler is None:
                self._event_handler = EventHandler()
            self._event_handler.connect(event_name, handler)
        else:
            if self.root._global_event_handler is None:
                self.root._global_event_handler = EventHandler()
            self.root._global_event_handler.connect(event_name, handler)

    def raiseEvent(self, event_name, *args):
        # Transfer event to local listeners
        if self._event_handler is not None:
            self._event_handler.raiseEvent(event_name, *args)

        # Transfer event to global listeners
        if self.root._global_event_handler is not None:
            self.root._global_event_handler.raiseEvent(event_name, *args)

    def setUniqueFieldName(self, field):
        key = field._name[:-2]
        try:
            self._field_array_count[key] += 1
        except KeyError:
            self._field_array_count[key] = 0
        field._name = key + "[%u]" % self._field_array_count[key]

    def readFirstFields(self, number):
        """
        Read first number fields if they are not read yet.

        Returns number of new added fields.
        """
        number = number - self.current_length
        if 0 < number:
            return self.readMoreFields(number)
        else:
            return 0

    def createFields(self):
        raise NotImplementedError()
    def __iter__(self):
        raise NotImplementedError()
    def __len__(self):
        raise NotImplementedError()
    def getField(self, key, const=True):
        raise NotImplementedError()
    def nextFieldAddress(self):
        raise NotImplementedError()
    def getFieldIndex(self, field):
        raise NotImplementedError()
    def readMoreFields(self, number):
        raise NotImplementedError()

