from js2py.base import *

def _get_conts(idl):
    def is_valid(c):
        try:
            exec(c)
            return 1
        except:
            pass
    return '\n'.join(filter(is_valid, (' '.join(e.strip(' ;').split()[-3:]) for e in idl.splitlines())))


default_attrs = {'writable':True, 'enumerable':True, 'configurable':True}


def compose_prototype(Class, attrs=default_attrs):
    prototype = Class()
    for i in dir(Class):
        e = getattr(Class, i)
        if hasattr(e, '__func__'):
            temp = PyJsFunction(e.__func__, FunctionPrototype)
            attrs = {k:v for k,v in attrs.iteritems()}
            attrs['value'] = temp
            prototype.define_own_property(i, attrs)
    return prototype


# Error codes

INDEX_SIZE_ERR = 1
DOMSTRING_SIZE_ERR = 2
HIERARCHY_REQUEST_ERR = 3
WRONG_DOCUMENT_ERR = 4
INVALID_CHARACTER_ERR = 5
NO_DATA_ALLOWED_ERR = 6
NO_MODIFICATION_ALLOWED_ERR = 7
NOT_FOUND_ERR = 8
NOT_SUPPORTED_ERR = 9
INUSE_ATTRIBUTE_ERR = 10
INVALID_STATE_ERR = 11
SYNTAX_ERR = 12
INVALID_MODIFICATION_ERR = 13
NAMESPACE_ERR = 14
INVALID_ACCESS_ERR = 15
VALIDATION_ERR = 16
TYPE_MISMATCH_ERR = 17

