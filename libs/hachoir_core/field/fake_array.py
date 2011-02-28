import itertools
from hachoir_core.field import MissingField

class FakeArray:
    """
    Simulate an array for GenericFieldSet.array(): fielset.array("item")[0] is
    equivalent to fielset.array("item[0]").

    It's possible to iterate over the items using::

        for element in fieldset.array("item"):
            ...

    And to get array size using len(fieldset.array("item")).
    """
    def __init__(self, fieldset, name):
        pos = name.rfind("/")
        if pos != -1:
            self.fieldset = fieldset[name[:pos]]
            self.name = name[pos+1:]
        else:
            self.fieldset = fieldset
            self.name = name
        self._format = "%s[%%u]" % self.name
        self._cache = {}
        self._known_size = False
        self._max_index = -1

    def __nonzero__(self):
        "Is the array empty or not?"
        if self._cache:
            return True
        else:
            return (0 in self)

    def __len__(self):
        "Number of fields in the array"
        total = self._max_index+1
        if not self._known_size:
            for index in itertools.count(total):
                try:
                    field = self[index]
                    total += 1
                except MissingField:
                    break
        return total

    def __contains__(self, index):
        try:
            field = self[index]
            return True
        except MissingField:
            return False

    def __getitem__(self, index):
        """
        Get a field of the array. Returns a field, or raise MissingField
        exception if the field doesn't exist.
        """
        try:
            value = self._cache[index]
        except KeyError:
            try:
                value = self.fieldset[self._format % index]
            except MissingField:
                self._known_size = True
                raise
            self._cache[index] = value
            self._max_index = max(index, self._max_index)
        return value

    def __iter__(self):
        """
        Iterate in the fields in their index order: field[0], field[1], ...
        """
        for index in itertools.count(0):
            try:
                yield self[index]
            except MissingField:
                raise StopIteration()

