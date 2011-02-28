from hachoir_core.field import FieldSet, ParserError

class StaticFieldSet(FieldSet):
    """
    Static field set: format class attribute is a tuple of all fields
    in syntax like:
       format = (
          (TYPE1, ARG1, ARG2, ...),
          (TYPE2, ARG1, ARG2, ..., {KEY1=VALUE1, ...}),
          ...
       )

    Types with dynamic size are forbidden, eg. CString, PascalString8, etc.
    """
    format = None  # You have to redefine this class variable
    _class = None

    def __new__(cls, *args, **kw):
        assert cls.format is not None, "Class attribute 'format' is not set"
        if cls._class is not cls.__name__:
            cls._class = cls.__name__
            cls.static_size = cls._computeStaticSize()
        return object.__new__(cls, *args, **kw)

    @staticmethod
    def _computeItemSize(item):
        item_class = item[0]
        if item_class.static_size is None:
            raise ParserError("Unable to get static size of field type: %s"
                % item_class.__name__)
        if callable(item_class.static_size):
            if isinstance(item[-1], dict):
                return item_class.static_size(*item[1:-1], **item[-1])
            else:
                return item_class.static_size(*item[1:])
        else:
            assert isinstance(item_class.static_size, (int, long))
            return item_class.static_size

    def createFields(self):
        for item in self.format:
            if isinstance(item[-1], dict):
                yield item[0](self, *item[1:-1], **item[-1])
            else:
                yield item[0](self, *item[1:])

    @classmethod
    def _computeStaticSize(cls, *args):
        return sum(cls._computeItemSize(item) for item in cls.format)

    # Initial value of static_size, it changes when first instance
    # is created (see __new__)
    static_size = _computeStaticSize

