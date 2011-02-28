from hachoir_core.field import Field, FieldSet, ParserError

class GenericVector(FieldSet):
    def __init__(self, parent, name, nb_items, item_class, item_name="item", description=None):
        # Sanity checks
        assert issubclass(item_class, Field)
        assert isinstance(item_class.static_size, (int, long))
        if not(0 < nb_items):
            raise ParserError('Unable to create empty vector "%s" in %s' \
                % (name, parent.path))
        size = nb_items * item_class.static_size
        self.__nb_items = nb_items
        self._item_class = item_class
        self._item_name = item_name
        FieldSet.__init__(self, parent, name, description, size=size)

    def __len__(self):
        return self.__nb_items

    def createFields(self):
        name = self._item_name + "[]"
        parser = self._item_class
        for index in xrange(len(self)):
            yield parser(self, name)

class UserVector(GenericVector):
    """
    To implement:
    - item_name: name of a field without [] (eg. "color" becomes "color[0]"),
      default value is "item"
    - item_class: class of an item
    """
    item_class = None
    item_name = "item"

    def __init__(self, parent, name, nb_items, description=None):
        GenericVector.__init__(self, parent, name, nb_items, self.item_class, self.item_name, description)

