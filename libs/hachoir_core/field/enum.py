def Enum(field, enum, key_func=None):
    """
    Enum is an adapter to another field: it will just change its display
    attribute. It uses a dictionary to associate a value to another.

    key_func is an optional function with prototype "def func(key)->key"
    which is called to transform key.
    """
    display = field.createDisplay
    if key_func:
        def createDisplay():
            try:
                key = key_func(field.value)
                return enum[key]
            except LookupError:
                return display()
    else:
        def createDisplay():
            try:
                return enum[field.value]
            except LookupError:
                return display()
    field.createDisplay = createDisplay
    field.getEnum = lambda: enum
    return field

