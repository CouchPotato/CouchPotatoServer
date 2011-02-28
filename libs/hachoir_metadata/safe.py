from hachoir_core.error import HACHOIR_ERRORS, warning

def fault_tolerant(func, *args):
    def safe_func(*args, **kw):
        try:
            func(*args, **kw)
        except HACHOIR_ERRORS, err:
            warning("Error when calling function %s(): %s" % (
                func.__name__, err))
    return safe_func

def getFieldAttribute(fieldset, key, attrname):
    try:
        field = fieldset[key]
        if field.hasValue():
            return getattr(field, attrname)
    except HACHOIR_ERRORS, err:
        warning("Unable to get %s of field %s/%s: %s" % (
            attrname, fieldset.path, key, err))
    return None

def getValue(fieldset, key):
    return getFieldAttribute(fieldset, key, "value")

def getDisplay(fieldset, key):
    return getFieldAttribute(fieldset, key, "display")

