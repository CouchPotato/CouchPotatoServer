from hachoir_core.tools import makeUnicode, normalizeNewline
from hachoir_core.error import HACHOIR_ERRORS
from hachoir_metadata import config
from hachoir_metadata.setter import normalizeString

MIN_PRIORITY = 100
MAX_PRIORITY = 999

QUALITY_FASTEST = 0.0
QUALITY_FAST = 0.25
QUALITY_NORMAL = 0.5
QUALITY_GOOD = 0.75
QUALITY_BEST = 1.0

class DataValue:
    def __init__(self, value, text):
        self.value = value
        self.text = text

class Data:
    def __init__(self, key, priority, description,
    text_handler=None, type=None, filter=None, conversion=None):
        """
        handler is only used if value is not string nor unicode, prototype:
           def handler(value) -> str/unicode
        """
        assert MIN_PRIORITY <= priority <= MAX_PRIORITY
        assert isinstance(description, unicode)
        self.metadata = None
        self.key = key
        self.description = description
        self.values = []
        if type and not isinstance(type, (tuple, list)):
            type = (type,)
        self.type = type
        self.text_handler = text_handler
        self.filter = filter
        self.priority = priority
        self.conversion = conversion

    def _createItem(self, value, text=None):
        if text is None:
            if isinstance(value, unicode):
                text = value
            elif self.text_handler:
                text = self.text_handler(value)
                assert isinstance(text, unicode)
            else:
                text = makeUnicode(value)
        return DataValue(value, text)

    def add(self, value):
        if isinstance(value, tuple):
            if len(value) != 2:
                raise ValueError("Data.add() only accept tuple of 2 elements: (value,text)")
            value, text = value
        else:
            text = None

        # Skip value 'None'
        if value is None:
            return

        if isinstance(value, (str, unicode)):
            value = normalizeString(value)
            if not value:
                return

        # Convert string to Unicode string using charset ISO-8859-1
        if self.conversion:
            try:
                new_value = self.conversion(self.metadata, self.key, value)
            except HACHOIR_ERRORS, err:
                self.metadata.warning("Error during conversion of %r value: %s" % (
                    self.key, err))
                return
            if new_value is None:
                dest_types = " or ".join(str(item.__name__) for item in self.type)
                self.metadata.warning("Unable to convert %s=%r (%s) to %s" % (
                    self.key, value, type(value).__name__, dest_types))
                return
            if isinstance(new_value, tuple):
                if text:
                    value = new_value[0]
                else:
                    value, text = new_value
            else:
                value = new_value
        elif isinstance(value, str):
            value = unicode(value, "ISO-8859-1")

        if self.type and not isinstance(value, self.type):
            dest_types = " or ".join(str(item.__name__) for item in self.type)
            self.metadata.warning("Key %r: value %r type (%s) is not %s" % (
                self.key, value, type(value).__name__, dest_types))
            return

        # Skip empty strings
        if isinstance(value, unicode):
            value = normalizeNewline(value)
            if config.MAX_STR_LENGTH \
            and config.MAX_STR_LENGTH < len(value):
                value = value[:config.MAX_STR_LENGTH] + "(...)"

        # Skip duplicates
        if value in self:
            return

        # Use filter
        if self.filter and not self.filter(value):
            self.metadata.warning("Skip value %s=%r (filter)" % (self.key, value))
            return

        # For string, if you have "verlongtext" and "verylo",
        # keep the longer value
        if isinstance(value, unicode):
            for index, item in enumerate(self.values):
                item = item.value
                if not isinstance(item, unicode):
                    continue
                if value.startswith(item):
                    # Find longer value, replace the old one
                    self.values[index] = self._createItem(value, text)
                    return
                if item.startswith(value):
                    # Find truncated value, skip it
                    return

        # Add new value
        self.values.append(self._createItem(value, text))

    def __len__(self):
        return len(self.values)

    def __getitem__(self, index):
        return self.values[index]

    def __contains__(self, value):
        for item in self.values:
            if value == item.value:
                return True
        return False

    def __cmp__(self, other):
        return cmp(self.priority, other.priority)

